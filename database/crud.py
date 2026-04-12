from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from database.schemas import UserSchema, VehicleCreateSchema, OrderCreateSchema
from database.user_models import User
from database.driver_models import Driver, TruckType
from database.order_models import Order

async def get_user_db(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def update_user_role_db(session: AsyncSession, user_id: int, role: str):
    await session.execute(update(User).where(User.id == user_id).values(role=role))
    await session.commit()

async def add_vehicle_db(session: AsyncSession, data: VehicleCreateSchema):
    # 1. Ensure TruckType exists
    result = await session.execute(select(TruckType).where(TruckType.name == data.type))
    truck_type = result.scalar_one_or_none()
    if not truck_type:
        truck_type = TruckType(name=data.type, max_weight=data.weight, max_volume=0)
        session.add(truck_type)
        await session.commit()
        await session.refresh(truck_type)
    
    # 2. Check if driver exists
    result = await session.execute(select(Driver).where(Driver.user_id == data.user_id))
    driver = result.scalar_one_or_none()
    
    if driver:
        # update
        driver.truck_number = data.number
        driver.truck_type_id = truck_type.id
        driver.capacity_ton = data.weight
        await session.commit()
    else:
        # insert
        new_driver = Driver(
            user_id=data.user_id,
            truck_type_id=truck_type.id,
            truck_number=data.number,
            capacity_ton=data.weight
        )
        session.add(new_driver)
        await session.commit()

async def set_online_status_db(session: AsyncSession, user_id: int, status: bool):
    result = await session.execute(select(Driver).where(Driver.user_id == user_id))
    driver = result.scalar_one_or_none()
    if driver:
        driver.is_available = status
        await session.commit()

async def update_location_db(session: AsyncSession, user_id: int, lat: float, lon: float):
    result = await session.execute(select(Driver).where(Driver.user_id == user_id))
    driver = result.scalar_one_or_none()
    if driver:
        driver.last_latitude = lat
        driver.last_longitude = lon
        driver.last_location_at = datetime.now(timezone.utc)
        await session.commit()

async def create_order_db(session: AsyncSession, data: OrderCreateSchema):
    # Require a generic TruckType if none matches
    result = await session.execute(select(TruckType).where(TruckType.name == data.cargo_type))
    truck_type = result.scalar_one_or_none()
    if not truck_type:
        truck_type = TruckType(name=data.cargo_type, max_weight=data.weight, max_volume=0)
        session.add(truck_type)
        await session.commit()
        await session.refresh(truck_type)
        
    truck_type_id = truck_type.id
    
    new_order = Order(
        customer_id=data.customer_id,
        cargo_name=f"Cargo {data.weight}t", # Default name constraint format
        weight=data.weight,
        from_city=data.from_address,
        to_city=data.to_address,
        required_truck_type_id=truck_type_id,
        price=data.price,
        pickup_date=datetime.now(timezone.utc)
    )
    session.add(new_order)
    await session.commit()
    return new_order

async def get_user_orders_db(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Order).where(Order.customer_id == user_id).order_by(Order.created_at.desc())
    )
    return result.scalars().all()

async def get_available_orders_db(session: AsyncSession):
    # Orders that are pending and don't have a driver yet
    result = await session.execute(
        select(Order).where(Order.status == 'PENDING', Order.driver_id == None).order_by(Order.created_at.desc())
    )
    return result.scalars().all()

async def cancel_order_db(session: AsyncSession, order_id: int, user_id: int):
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.customer_id == user_id)
    )
    order = result.scalar_one_or_none()
    if order:
        order.status = 'CANCELLED'
        await session.commit()
        return True
    return False
