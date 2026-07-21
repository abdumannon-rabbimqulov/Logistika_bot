from aiogram import Router
from .start import router as start_router
from .verification_code import router as verification_code_router
from .dispatch import router as dispatch_router

main_router = Router()

main_router.include_router(start_router)
main_router.include_router(verification_code_router)
main_router.include_router(dispatch_router)
