import logging
from sqlalchemy.ext.asyncio import AsyncSession
from config.config import client, MODEL_NAME, SYSTEM_INSTRUCTION, async_session
from order import crud as order_crud, schemas as order_schemas
from driver import crud as driver_crud

logger = logging.getLogger(__name__)

class LogistikaToolkit:
    """AI Agent uchun asboblar to'plami (Tools)."""
    
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def create_order(
        self, 
        cargo_name: str, 
        weight: float, 
        from_city: str, 
        to_city: str, 
        price: float,
        required_truck_type_id: int
    ) -> str:
        """
        Yangi yuk buyurtmasini yaratish.
        Parametrlar: cargo_name (yuk nomi), weight (vazni tonnada), from_city (qayerdan), to_city (qayerga), price (narxi), required_truck_type_id (mashina turi ID).
        """
        try:
            # Pydantic schema tayyorlash
            order_data = order_schemas.OrderCreate(
                customer_id=self.user_id,
                cargo_name=cargo_name,
                weight=weight,
                price=price,
                required_truck_type_id=required_truck_type_id,
                waypoints=[
                    order_schemas.OrderWaypointCreate(sequence=1, waypoint_type="pickup", city=from_city),
                    order_schemas.OrderWaypointCreate(sequence=2, waypoint_type="delivery", city=to_city)
                ]
            )
            order = await order_crud.create_order(self.db, order_data)
            return f"Muvaffaqiyatli! Buyurtma #{order.id} yaratildi. Yuk: {cargo_name}, Narxi: {price} UZS."
        except Exception as e:
            logger.error(f"Error creating order via AI: {e}")
            return f"Xatolik yuz berdi: {str(e)}"

    async def list_truck_types(self) -> str:
        """Yuk mashinalari turlari va ularning ID larini qaytaradi."""
        types = await driver_crud.get_all_truck_types(self.db)
        if not types:
            return "Hozircha mashina turlari bazada yo'q."
        res = "Mavjud yuk mashinalari:\n"
        for t in types:
            res += f"- ID {t.id}: {t.name} ({t.max_weight_ton} tonnagacha)\n"
        return res

    async def list_my_orders(self) -> str:
        """Foydalanuvchining barcha buyurtmalarini ko'rish."""
        orders = await order_crud.get_all_orders(self.db, customer_id=self.user_id)
        if not orders:
            return "Sizda hali buyurtmalar yo'q."
        res = "Sizning buyurtmalaringiz:\n"
        for o in orders:
            res += f"- #{o.id} {o.cargo_name} ({o.status})\n"
        return res

# AI Agent tomonidan chaqirilishi mumkin bo'lgan funksiyalar deklaratsiyasi
TOOLS_DECLARATION = [
    {
        "name": "create_order",
        "description": "Yangi yuk buyurtmasini yaratadi. Masalan: 'Toshkentdan Andijonga 20 tonna olma olib borish uchun 2 mln so'mlik buyurtma yarat'.",
        "parameters": {
            "type": "object",
            "properties": {
                "cargo_name": {"type": "string", "description": "Yuk nomi (masalan: Olma, Qurilish mollari)"},
                "weight": {"type": "number", "description": "Yuk vazni (tonnada)"},
                "from_city": {"type": "string", "description": "Yuk olinadigan shahar"},
                "to_city": {"type": "string", "description": "Yuk yetkaziladigan shahar"},
                "price": {"type": "number", "description": "Taklif qilingan narx (UZS)"},
                "required_truck_type_id": {"type": "integer", "description": "Mashina turi ID si (standart: 1)"}
            },
            "required": ["cargo_name", "weight", "from_city", "to_city", "price"]
        }
    },
    {
        "name": "list_truck_types",
        "description": "Mavjud yuk mashinalari turlarini ko'rish."
    },
    {
        "name": "list_my_orders",
        "description": "Foydalanuvchining o'z xisobidagi buyurtmalarni ko'rish."
    }
]

class LogistikaAgent:
    """Gemini AI Agent boshqaruvchisi."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.chat = None

    async def _get_chat_history(self, db: AsyncSession, chat_id: int):
        # Kelgusida bazadan eslab qolish uchun
        pass

    async def process_message(self, message_text: str, chat_id: int, on_action_callback=None):
        """Xabarni qayta ishlash va kerak bo'lsa tool chaqirish."""
        if not client:
            return "AI Agent hozircha o'chiq (API_KEY sozlanmagan)."

        # Agentga tool-lar haqida malumot beramiz
        # google-genai SDK tool chaqirish
        try:
            # Gemini bilan muloqot
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=message_text,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "tools": [{"function_declarations": TOOLS_DECLARATION}]
                }
            )
            
            # Agar tool chaqirilgan bo'lsa
            if response.candidates[0].content.parts and response.candidates[0].content.parts[0].function_call:
                func_call = response.candidates[0].content.parts[0].function_call
                func_name = func_call.name
                args = func_call.args
                
                if on_action_callback:
                    await on_action_callback(f"Bajarilmoqda: {func_name}...")
                
                async with async_session() as db:
                    toolkit = LogistikaToolkit(db, self.user_id)
                    tool_func = getattr(toolkit, func_name, None)
                    
                    if tool_func:
                        result = await tool_func(**args)
                        
                        # Natijani agentga qaytaramiz (final javob uchun)
                        # Bu yerda ikkinchi iteration kerak
                        final_response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=[
                                message_text,
                                response.candidates[0].content,
                                {
                                    "parts": [{
                                        "function_response": {
                                            "name": func_name,
                                            "response": {"content": result}
                                        }
                                    }]
                                }
                            ],
                            config={
                                "system_instruction": SYSTEM_INSTRUCTION,
                                "tools": [{"function_declarations": TOOLS_DECLARATION}]
                            }
                        )
                        return final_response.text
                    else:
                        return "Kechirasiz, bunday funksiya topilmadi."
            
            return response.text

        except Exception as e:
            logger.error(f"AI Agent Error: {e}")
            return f"Kechirasiz, muammo yuz berdi: {str(e)}"

    async def process_audio(self, audio_url: str, chat_id: int, on_action_callback=None):
        """Ovozli xabarni qayta ishlash (Kelgusida audio bytes orqali)."""
        # Hozircha ovozli xabar kelganda uni matnga aylantirish yoki audio modeldan foydalanish mumkin
        # Gemini 1.5 Flash ovozni yaxshi tushunadi
        return "Ovozli xabar qabul qilindi. Hozircha uni qayta ishlash ustida ishlamoqdamiz."
