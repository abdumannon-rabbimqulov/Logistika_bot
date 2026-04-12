from config.config import init_db, engine, async_session
from database import crud
from database.schemas import VehicleCreateSchema, OrderCreateSchema

class DatabaseHelper:
    async def connect(self):
        await init_db()
        
    async def close(self):
        await engine.dispose()
        
    async def get_user(self, user_id: int):
        async with async_session() as session:
            return await crud.get_user_db(session, user_id)
            
    async def update_user_role(self, user_id: int, role: str):
        async with async_session() as session:
            return await crud.update_user_role_db(session, user_id, role)
            
    async def add_vehicle(self, user_id: int, data_dict: dict):
        async with async_session() as session:
            schema = VehicleCreateSchema(
                user_id=user_id,
                model=data_dict.get("model", ""),
                number=data_dict.get("number", ""),
                type=data_dict.get("type", ""),
                weight=data_dict.get("weight", 0.0)
            )
            return await crud.add_vehicle_db(session, schema)
            
    async def set_online_status(self, user_id: int, status: bool):
        async with async_session() as session:
            return await crud.set_online_status_db(session, user_id, status)
            
    async def update_location(self, user_id: int, lat: float, lon: float):
        async with async_session() as session:
            return await crud.update_location_db(session, user_id, lat, lon)
    async def create_order(self, customer_id: int, data_dict: dict):
        async with async_session() as session:
            schema = OrderCreateSchema(
                customer_id=customer_id,
                cargo_type=data_dict.get("cargo_type", ""),
                from_address=data_dict.get("from_address", ""),
                to_address=data_dict.get("to_address", ""),
                weight=float(data_dict.get("weight", 0)),
                price=float(data_dict.get("price", 0))
            )
            return await crud.create_order_db(session, schema)

    async def get_user_orders(self, user_id: int):
        async with async_session() as session:
            return await crud.get_user_orders_db(session, user_id)

    async def get_available_orders(self):
        async with async_session() as session:
            return await crud.get_available_orders_db(session)

    async def cancel_order(self, order_id: int, user_id: int):
        async with async_session() as session:
            return await crud.cancel_order_db(session, order_id, user_id)

db = DatabaseHelper()
