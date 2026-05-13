from aiogram import Router
from .start import router as start_router
from .location import router as location_router
from .verification_code import router as verification_code_router

# Base router for all handlers
main_router = Router()

# Include sub-routers (Order matters!)
main_router.include_router(start_router)
main_router.include_router(location_router)
main_router.include_router(verification_code_router)
