from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.reply import get_main_menu, get_cargo_type_keyboard, get_confirmation_keyboard
from db import db

router = Router()

class OrderStates(StatesGroup):
    choosing_type = State()
    entering_from = State()
    entering_to = State()
    entering_weight = State()
    entering_price = State()
    confirming = State()

@router.message(F.text.in_(["🚛 Buyurtma berish", "🚛 Заказать перевозку"]))
async def start_order(message: types.Message, state: FSMContext, _):
    await state.set_state(OrderStates.choosing_type)
    await message.answer(_("order_start_msg"), reply_markup=get_cargo_type_keyboard(_))

@router.message(OrderStates.choosing_type)
async def process_type(message: types.Message, state: FSMContext, _):
    if message.text == _("btn_back"):
        await state.clear()
        await message.answer(_("welcome"), reply_markup=get_main_menu(_))
        return
    
    await state.update_data(cargo_type=message.text)
    await state.set_state(OrderStates.entering_from)
    await message.answer(_("order_from_msg"), reply_markup=types.ReplyKeyboardRemove())

@router.message(OrderStates.entering_from)
async def process_from(message: types.Message, state: FSMContext, _):
    await state.update_data(from_address=message.text)
    await state.set_state(OrderStates.entering_to)
    await message.answer(_("order_to_msg"))

@router.message(OrderStates.entering_to)
async def process_to(message: types.Message, state: FSMContext, _):
    await state.update_data(to_address=message.text)
    await state.set_state(OrderStates.entering_weight)
    await message.answer(_("order_weight_msg"))

@router.message(OrderStates.entering_weight)
async def process_weight(message: types.Message, state: FSMContext, _):
    await state.update_data(weight=message.text)
    await state.set_state(OrderStates.entering_price)
    await message.answer(_("order_price_msg"))

@router.message(OrderStates.entering_price)
async def process_price(message: types.Message, state: FSMContext, _):
    await state.update_data(price=message.text)
    data = await state.get_data()
    
    # Python'da 'from' rezerv qilingan so'z, shuning uchun dictionary ishlatamiz
    params = {
        "type": data['cargo_type'],
        "from": data['from_address'],
        "to": data['to_address'],
        "weight": data['weight'],
        "price": data['price']
    }
    
    confirm_text = _("order_confirm_msg", **params)
    
    await state.set_state(OrderStates.confirming)
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=get_confirmation_keyboard(_))

@router.message(OrderStates.confirming, F.text.in_(["✅ Tasdiqlash", "✅ Подтвердить"]))
async def confirm_order(message: types.Message, state: FSMContext, _):
    # In a real app, we would save to the database here
    # await db.create_order(data)
    await state.clear()
    await message.answer(_("order_created_msg"), reply_markup=get_main_menu(_))

@router.message(OrderStates.confirming, F.text.in_(["❌ Bekor qilish", "❌ Отмена"]))
async def cancel_order(message: types.Message, state: FSMContext, _):
    await state.clear()
    await message.answer(_("welcome"), reply_markup=get_main_menu(_))
