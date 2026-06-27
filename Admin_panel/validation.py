from fastapi import Depends, HTTPException, status

from config.config import ADMIN_IDS
from users.auth import get_current_user
from users.models import User, UserRole


async def is_admin(current_user: User = Depends(get_current_user)) -> User:

    if current_user.role == UserRole.ADMIN:
        return current_user
    if current_user.id in ADMIN_IDS:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sizda ushbu amalni bajarish uchun huquq yo'q (Admin emassiz)!",
    )
