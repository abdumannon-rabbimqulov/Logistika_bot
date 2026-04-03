# import os
# import logging
# from aiogram import Router, types, F, Bot
# from aiogram.fsm.context import FSMContext
# from config import client, MODEL_NAME, SYSTEM_INSTRUCTION
# from google.genai import types as genai_types
#
# router = Router()
#
# @router.message(F.voice)
# async def voice_ai_handler(message: types.Message, bot: Bot, _):
#     """Handle voice messages using Gemini 1.5 Flash."""
#     try:
#         # Show 'typing' action or equivalent for voice
#         sent_msg = await message.reply("Ovozli xabar tahlil qilinmoqda... 🎤⏳")
#
#         # Get voice file info
#         voice = message.voice
#         file_id = voice.file_id
#         file = await bot.get_file(file_id)
#         file_path = file.file_path
#
#         # Download file to memory
#         voice_bytes = await bot.download_file(file_path)
#         voice_data = voice_bytes.getvalue()
#
#         # Send to Gemini
#         response = client.models.generate_content(
#             model=MODEL_NAME,
#             config=genai_types.GenerateContentConfig(
#                 system_instruction=SYSTEM_INSTRUCTION,
#                 temperature=0.7
#             ),
#             contents=[
#                 genai_types.Part.from_bytes(data=voice_data, mime_type="audio/ogg"),
#                 "Ushbu ovozli xabarni tahlil qiling va logistika bo'yicha yordam bering."
#             ]
#         )
#
#         # Reply to user
#         await sent_msg.edit_text(response.text)
#
#     except Exception as e:
#         logging.error(f"Voice AI Error: {e}")
#         await message.reply("Kechirasiz, ovozli xabarni tahlil qilishda xatolik yuz berdi. Iltimos, matn ko'rinishida yozing.")
#
# @router.message(F.text)
# async def text_ai_handler(message: types.Message, state: FSMContext, _):
#     """Handle text messages using Gemini 1.5 Flash."""
#     # Check if user is in an active FSM state (e.g. registration)
#     current_state = await state.get_state()
#     if current_state:
#         # If user is in a state, we don't want AI to interfere
#         # unless it's explicitly designed to.
#         # For now, let other handlers take over.
#         return
#
#     try:
#         # Send to Gemini
#         response = client.models.generate_content(
#             model=MODEL_NAME,
#             config=genai_types.GenerateContentConfig(
#                 system_instruction=SYSTEM_INSTRUCTION,
#                 temperature=0.7
#             ),
#             contents=message.text
#         )
#
#         if response.text:
#             await message.reply(response.text)
#
#     except Exception as e:
#         logging.error(f"Text AI Error: {e}")
#