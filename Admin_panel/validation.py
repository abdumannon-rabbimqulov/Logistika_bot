import os
from fastapi import Header, HTTPException, Depends, status
from dotenv import load_dotenv
from users.auth import get_current_user
from users.models import User

load_dotenv()


ADMIN_ID = os.getenv("ADMIN")

async def is_admin(current_user: User = Depends(get_current_user)):
    if current_user.id != ADMIN_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizda ushbu amalni bajarish uchun huquq yo'q (Admin emassiz)!"
        )
    return current_user