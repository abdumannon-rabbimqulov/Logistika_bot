import logging
from sqlalchemy import select, update
from datetime import datetime
from config.config import engine, async_session, init_db
from config.models import User, Driver, TruckType

class Database:
    async def connect(self):
        await init_db()
        logging.info("Database initialized with SQLAlchemy.")

    async def close(self):
        await engine.dispose()
        logging.info("Database connection closed.")

    async def get_user(self, user_id: int):
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return {
                    'id': user.id,
                    'full_name': user.full_name,
                    'first_name': user.full_name.split()[0] if user.full_name else 'User',
                    'username': user.username,
                    'role': user.role,
                    'balance': float(user.balance) if user.balance else 0.0,
                    'phone_number': user.phone_number,
                    'language': user.language
                }
            return None

    async def add_user_to_db(self, user_id: int, full_name: str, username: str):
        async with async_session() as session:
            user = User(
                id=user_id,
                full_name=full_name,
                username=username,
                role='guest',
                balance=0.0
            )
            session.add(user)
            await session.commit()

    async def update_user_language(self, user_id: int, lang_code: str):
        async with async_session() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(language=lang_code)
            )
            await session.commit()

    async def update_user_role(self, user_id: int, role: str):
        async with async_session() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(role=role)
            )
            await session.commit()

    async def add_vehicle(self, user_id: int, data: dict):
        async with async_session() as session:
            truck_type_str = data.get('type')
            truck_type = TruckType.TENT
            for t in TruckType:
                if t.value.lower() == str(truck_type_str).lower():
                    truck_type = t
                    break
            
            length = data.get('length', 0)
            width = data.get('width', 0)
            height = data.get('height', 0)
            m3 = length * width * height

            driver = Driver(
                user_id=user_id,
                truck_type=truck_type,
                truck_number=data.get('number', 'UNKNOWN'),
                capacity_ton=data.get('weight', 0.0),
                capacity_m3=m3,
                current_city="Unknown",
                is_available=True
            )
            session.add(driver)
            await session.commit()

    async def set_online_status(self, user_id: int, is_online: bool):
        async with async_session() as session:
            await session.execute(
                update(Driver).where(Driver.user_id == user_id).values(is_available=is_online)
            )
            await session.commit()

    async def update_location(self, user_id: int, lat: float, lon: float):
        async with async_session() as session:
            await session.execute(
                update(Driver).where(Driver.user_id == user_id).values(
                    last_latitude=lat,
                    last_longitude=lon,
                    is_live_location_active=True,
                    last_location_at=datetime.utcnow()
                )
            )
            await session.commit()

db = Database()
