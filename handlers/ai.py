from aiogram import Router, types, F
from handlers.ai_agent import agent
import logging

router = Router()

@router.message(F.text)
async def ai_message_handler(message: types.Message):
    """
    Fallback handler that sends non-command text messages to the AI Agent.
    """
    user_id = message.from_user.id
    text = message.text
    
    # We show a "typing" status while waiting for AI
    await message.bot.send_chat_action(message.chat.id, action="typing")
    
    response_text = await agent.process_text(user_id, text)
    
    if response_text:
        await message.answer(response_text)
    else:
        await message.answer("Kechirasiz, yordam bera olmayman.")

@router.message(F.voice)
async def ai_voice_handler(message: types.Message):
    """
    Handles voice messages by sending them to the AI Agent (if multi-modal is supported).
    For now, we'll notify that we are working on it, 
    or just try to process if the agent supports it.
    """
    await message.answer("Ovozli xabaringiz qabul qilindi. Hozircha matnli xabarlardan foydalaning, ovozli xizmat integratsiya qilinmoqda.")
