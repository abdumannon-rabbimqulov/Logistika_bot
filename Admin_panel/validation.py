from fastapi import Depends, HTTPException, status

from config.config import ADMIN_IDS
from users.auth import get_current_user
from users.models import User


async def is_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.id not in ADMIN_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizda ushbu amalni bajarish uchun huquq yo'q (Admin emassiz)!",
        )
    return current_user
