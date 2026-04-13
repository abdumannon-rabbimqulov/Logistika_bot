from fastapi import FastAPI
from config.config import engine,Base
from users.models import User
from driver.models import Driver,DriverAnnouncement,TruckType,AnnouncementOffer
from order.models import OrderOffer,Order

app = FastAPI(title="FastAPI")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
