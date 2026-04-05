import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from config.config import client, MODEL_NAME, SYSTEM_INSTRUCTION
from google.genai import types as genai_types

router = Router()

def get_gemini_config() -> genai_types.GenerateContentConfig:
    return genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7
    )

# Gemini ga so'rov yuborish umumiy funksiya
async def ask_gemini(contents) -> str | None:
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            config=get_gemini_config(),
            contents=contents
        )
        return response.text if response.text else None
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        return None

@router.message(F.voice)
async def voice_ai_handler(message: types.Message, bot: Bot, _):
    sent_msg = await message.reply("Ovozli xabar tahlil qilinmoqda... 🎤⏳")

    try:
        # Fayl yuklab olish
        file = await bot.get_file(message.voice.file_id)
        voice_bytes = await bot.download_file(file.file_path)

        # Gemini ga yuborish
        result = await ask_gemini([
            genai_types.Part.from_bytes(
                data=voice_bytes.getvalue(),
                mime_type="audio/ogg"
            ),
            "Ushbu ovozli xabarni tahlil qiling va logistika bo'yicha yordam bering."
        ])

        # Natijani ko'rsatish
        await sent_msg.edit_text(
            result or "Javob olishda muammo yuz berdi. Qaytadan urinib ko'ring."
        )

    except Exception as e:
        logging.error(f"Voice Handler Error: {e}")
        await sent_msg.edit_text(
            "Kechirasiz, ovozli xabarni tahlil qilishda xatolik. Matn ko'rinishida yozing."
        )

@router.message(F.text)
async def text_ai_handler(message: types.Message, state: FSMContext, _):
    if await state.get_state():
        return

    result = await ask_gemini(message.text)

    if result:
        await message.reply(result)
    else:
        # ✅ Endi foydalanuvchi xato haqida biladi
        await message.reply(
            "Kechirasiz, javob olishda xatolik yuz berdi. Qaytadan urinib ko'ring."
        )