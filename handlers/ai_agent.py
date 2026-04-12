import logging
import json
from config.config import client, MODEL_NAME, SYSTEM_INSTRUCTION
from handlers.logistika_actions import LOGISTIKA_TOOLS, ACTION_MAP

logger = logging.getLogger(__name__)

class LogistikaAgent:
    def __init__(self):
        self.model_id = MODEL_NAME
        # In-memory session storage: {user_id: [parts, ...]}
        self.sessions = {}
        self.max_history = 20 # Keep last 20 turns

    def _get_session_history(self, user_id: int):
        if user_id not in self.sessions:
            self.sessions[user_id] = []
        return self.sessions[user_id]

    async def process_text(self, user_id: int, text: str):
        """
        Processes user text through Gemini with session memory and handles tool calls.
        """
        try:
            history = self._get_session_history(user_id)
            
            # Add user message to history
            current_message = {"role": "user", "parts": [{"text": text}]}
            
            # Prepare contents for Gemini (History + Current Message)
            # generate_content's 'contents' parameter can be a list of conversation turns
            contents = history + [current_message]

            # Generate response with tools
            response = client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "tools": [{"function_declarations": LOGISTIKA_TOOLS}]
                }
            )

            if not response.candidates or not response.candidates[0].content.parts:
                return "Kechirasiz, xabarni tushuna olmadim."

            res_content = response.candidates[0].content
            parts = res_content.parts
            tool_calls = [p.function_call for p in parts if p.function_call]
            
            if tool_calls:
                # Add the model's tool call turn to history
                history.append(current_message)
                history.append({"role": "model", "parts": parts})
                
                tool_results_parts = []
                for fc in tool_calls:
                    tool_name = fc.name
                    args = fc.args or {}
                    logger.info(f"AI calling tool: {tool_name} with args: {args}")
                    
                    if tool_name in ACTION_MAP:
                        action_func = ACTION_MAP[tool_name]
                        try:
                            if tool_name in ["create_order", "cancel_order", "set_driver_status"]:
                                result = await action_func(user_id=user_id, **args)
                            elif tool_name in ["get_my_orders", "get_profile"]:
                                result = await action_func(user_id=user_id)
                            else: # search_orders, get_help
                                result = await action_func()
                        except Exception as e:
                            logger.error(f"Action {tool_name} failed: {e}")
                            result = {"status": "error", "message": str(e)}
                            
                        tool_results_parts.append(
                            {"function_response": {"name": tool_name, "response": result}}
                        )
                    else:
                        tool_results_parts.append(
                            {"function_response": {"name": tool_name, "response": {"status": "error", "message": "Tool not found"}}}
                        )
                
                # Add tool results turn to history and send back for final natural response
                tool_turn = {"role": "tool", "parts": tool_results_parts}
                history.append(tool_turn)
                
                final_response = client.models.generate_content(
                    model=self.model_id,
                    contents=history, # Now history contains [..., user, model(call), tool(resp)]
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "tools": [{"function_declarations": LOGISTIKA_TOOLS}]
                    }
                )
                
                # Add final model response to history
                if final_response.candidates and final_response.candidates[0].content.parts:
                    final_parts = final_response.candidates[0].content.parts
                    history.append({"role": "model", "parts": final_parts})
                    
                    # Trim history
                    if len(self.sessions[user_id]) > self.max_history:
                        self.sessions[user_id] = self.sessions[user_id][-self.max_history:]
                        
                    return final_response.text
                return "Amal bajarildi, lekin xulosa qilishda xatolik yuz berdi."
            
            else:
                # No tool call, just a regular response
                # Add to history
                history.append(current_message)
                history.append({"role": "model", "parts": parts})
                
                # Trim history
                if len(self.sessions[user_id]) > self.max_history:
                    self.sessions[user_id] = self.sessions[user_id][-self.max_history:]
                    
                return response.text

        except Exception as e:
            logger.error(f"Error in LogistikaAgent.process_text: {e}")
            import traceback
            traceback.print_exc()
            return f"Xatolik yuz berdi: {str(e)}"

# Global instance
agent = LogistikaAgent()
