from aiogram import Router
from .start import router as start_router
from .driver_reg import router as driver_reg_router
from .location import router as location_router
from .menu import router as menu_router
from .ai import router as ai_router
from .order import router as order_router

# Base router for all handlers
main_router = Router()

# Include sub-routers (Order matters!)
main_router.include_router(start_router)
main_router.include_router(order_router)
main_router.include_router(menu_router)
main_router.include_router(driver_reg_router)
main_router.include_router(location_router)

# AI router should be LAST to act as a fallback and specialized assistant
main_router.include_router(ai_router)
