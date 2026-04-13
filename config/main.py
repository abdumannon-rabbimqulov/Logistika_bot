from fastapi import FastAPI
from config.config import engine,Base
from users.models import User
from driver.models import Driver,DriverAnnouncement,TruckType,AnnouncementOffer
from order.models import OrderOffer,Order
from driver.router import router as driver_router
from users.router import router as auth_router

app = FastAPI(title="FastAPI")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(driver_router)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])