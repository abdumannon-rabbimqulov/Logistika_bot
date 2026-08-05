"""JWT tekshiruvi — asosiy ilovaga so'rov yubormasdan.

Token asosiy ilovada (`users/auth.py`) beriladi va `SECRET_KEY` ikkala xizmatda bir
xil, shuning uchun bu yerda uni mahalliy tekshirish kifoya. Rol esa tokendagi
`role` claim'idan olinadi (`users/auth.py: token_payload_for`).

Nega bu yetarli: support xizmati faqat "kim yozdi / bu odam xodimmi" degan savolga
javob berishi kerak, pulga yoki buyurtma o'zgartirishga tegmaydi. Rol tokenda
eskirgan bo'lishi mumkin (admin rolni endigina o'zgartirgan bo'lsa) — token
muddati (`ACCESS_TOKEN_EXPIRE_MINUTES`, standart 60 daqiqa) bu oynani cheklaydi.
Moliyaviy yoki buzg'unchi amallar baribir asosiy ilovada bo'ladi, u yerda esa rol
HAR SAFAR bazadan o'qiladi.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from support_service.config import ALGORITHM, SECRET_KEY, STAFF_ROLES

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str | None

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None:
        raise _unauthorized("Avtorizatsiya tokeni yuborilmadi")

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _unauthorized("Yaroqsiz yoki muddati o'tgan token") from exc

    # Faqat `access` token: refresh yoki parol tiklash tokeni bilan kirib bo'lmasin.
    if payload.get("type") != "access":
        raise _unauthorized("Bu token turi bilan kirish mumkin emas")

    sub = payload.get("sub")
    if not sub:
        raise _unauthorized("Token tarkibi xato")

    return Principal(user_id=int(sub), role=payload.get("role"))


async def require_staff(principal: Principal = Depends(get_principal)) -> Principal:
    """Faqat admin yoki menejer.

    Eski (rolsiz) tokenlar bu yerdan o'tmaydi — `role` claim'i `None` bo'ladi.
    Bu ataylab: xodim huquqini taxminga asoslab berish mumkin emas, foydalanuvchi
    qayta login qilishi kerak.
    """
    if not principal.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat qo'llab-quvvatlash xodimlari (admin/menejer) uchun",
        )
    return principal
