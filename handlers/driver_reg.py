from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import db
from keyboards.reply import get_driver_menu, get_cancel_back_keyboard, get_role_keyboard

router = Router()

class DriverReg(StatesGroup):
    model = State()
    number = State()
    type = State()
    weight = State()
    dimensions = State()
    car_photo = State()
    license_photo = State()

back_map = {
    DriverReg.number: DriverReg.model,
    DriverReg.type: DriverReg.number,
    DriverReg.weight: DriverReg.type,
    DriverReg.dimensions: DriverReg.weight,
    DriverReg.car_photo: DriverReg.dimensions,
    DriverReg.license_photo: DriverReg.car_photo
}

@router.message(F.text.in_(["🚚 Haydovchi", "🚚 Водитель"]))
async def start_driver_registration(message: types.Message, state: FSMContext, _):
    await state.set_state(DriverReg.model)
    await message.answer(_("driver_reg_start"), reply_markup=get_cancel_back_keyboard(_))

@router.message(F.text.in_(["⬅️ Orqaga", "⬅️ Назад"]))
async def process_back(message: types.Message, state: FSMContext, _):
    current_state = await state.get_state()
    
    # Holatlar va ularga mos savollar xaritasi
    back_prompts = {
        DriverReg.number.state: (DriverReg.model, _("driver_reg_start")),
        DriverReg.type.state: (DriverReg.number, _("driver_reg_number")),
        DriverReg.weight.state: (DriverReg.type, _("driver_reg_type")),
        DriverReg.dimensions.state: (DriverReg.weight, _("driver_reg_weight")),
        DriverReg.car_photo.state: (DriverReg.dimensions, _("driver_reg_dimensions")),
        DriverReg.license_photo.state: (DriverReg.car_photo, _("driver_reg_car_photo")),
    }

    if current_state == DriverReg.model.state:
        await state.clear()
        await message.answer(_("select_role"), reply_markup=get_role_keyboard(_))
        return

    if current_state in back_prompts:
        prev_state, prompt = back_prompts[current_state]
        await state.set_state(prev_state)
        await message.answer(prompt, reply_markup=get_cancel_back_keyboard(_))

@router.message(F.text.in_(["❌ Bekor qilish", "❌ Отмена"]))
async def process_cancel(message: types.Message, state: FSMContext, _):
    await state.clear()
    await message.answer(_("select_role"), reply_markup=get_role_keyboard(_))

@router.message(DriverReg.model)
async def process_model(message: types.Message, state: FSMContext, _):
    await state.update_data(model=message.text)
    await state.set_state(DriverReg.number)
    await message.answer(_("driver_reg_number"), reply_markup=get_cancel_back_keyboard(_))

@router.message(DriverReg.number)
async def process_number(message: types.Message, state: FSMContext, _):
    await state.update_data(number=message.text)
    await state.set_state(DriverReg.type)
    await message.answer(_("driver_reg_type"), reply_markup=get_cancel_back_keyboard(_))

@router.message(DriverReg.type)
async def process_type(message: types.Message, state: FSMContext, _):
    await state.update_data(type=message.text)
    await state.set_state(DriverReg.weight)
    await message.answer(_("driver_reg_weight"), reply_markup=get_cancel_back_keyboard(_))

@router.message(DriverReg.weight)
async def process_weight(message: types.Message, state: FSMContext, _):
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(weight=weight)
        await state.set_state(DriverReg.dimensions)
        await message.answer(_("driver_reg_dimensions"), reply_markup=get_cancel_back_keyboard(_))
    except ValueError:
        await message.answer(_("invalid_weight"))

@router.message(DriverReg.dimensions)
async def process_dimensions(message: types.Message, state: FSMContext, _):
    try:
        dims = message.text.replace(',', '.').replace('x', ' ').replace('*', ' ').split()
        if len(dims) == 3:
            length, width, height = map(float, dims)
            await state.update_data(length=length, width=width, height=height)
            await state.set_state(DriverReg.car_photo)
            await message.answer(_("driver_reg_car_photo"), reply_markup=get_cancel_back_keyboard(_))
        else:
             await message.answer(_("invalid_dimensions"))
    except ValueError:
        await message.answer(_("invalid_dimensions_format"))

@router.message(DriverReg.car_photo, F.photo)
async def process_car_photo(message: types.Message, state: FSMContext, _):
    photo_id = message.photo[-1].file_id
    await state.update_data(car_photo=photo_id)
    await state.set_state(DriverReg.license_photo)
    await message.answer(_("driver_reg_license_photo"), reply_markup=get_cancel_back_keyboard(_))

@router.message(DriverReg.license_photo, F.photo)
async def process_license_photo(message: types.Message, state: FSMContext, _):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    data['license_photo'] = photo_id

    # Save to DB
    await db.update_user_role(message.from_user.id, 'driver')
    await db.add_vehicle(message.from_user.id, data)
    
    await state.clear()
    await message.answer(_("driver_reg_success"), reply_markup=get_driver_menu(_, is_online=False))
