from aiogram import Router
from .start import router as start_router
from .admin import router as admin_router

# Base router for all handlers
main_router = Router()

# Include sub-routers (Order matters!)
main_router.include_router(admin_router)
main_router.include_router(start_router)
