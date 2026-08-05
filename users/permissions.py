"""Rolga asoslangan kirish nazorati (RBAC) uchun yagona joy.

Nega kerak edi: ilgari har bir rol uchun alohida dependency yozilgan
(`users/auth.py`: `get_current_admin`, `get_current_sender`), qolgan tekshiruvlar esa
endpointlar ichida `if current_user.role != UserRole.DRIVER: raise 403` ko'rinishida
sochilib yotardi (`order/router.py:101, 457, 515, 531`). Yangi rol qo'shilganda kimning
nimaga huquqi borligini bitta joydan ko'rib bo'lmasdi va bitta joyni unutish osongina
huquq teshigiga aylanardi.

Endi butun matritsa shu faylda:

    ADMIN    — hamma narsa, shu jumladan MOLIYA (`/system/...` balans, komissiya)
    MANAGER  — buyurtma holati + yuk mashinasini biriktirish. MOLIYA YO'Q.
    SENDER   — o'z buyurtmalarini yaratish/tahrirlash, o'z narxini boshqarish
    DRIVER   — taklif qabul qilish, marshrut nuqtalarini belgilash
    GUEST    — faqat `/auth/select-role`

`is_admin` ATAYLAB manager'ni o'tkazmaydi: `/system` ostidagi barcha moliyaviy
endpointlar (`Admin_panel/router.py`) o'sha dependency'ga tayanadi, shuning uchun
manager uchun moliya bo'limi qo'shimcha kodsiz, avtomatik yopiq bo'ladi. Manager
uchun ruxsat etilgan amallar alohida `/manager` router'ida (`manager/router.py`).
"""

from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, HTTPException, status

from config.config import ADMIN_IDS
from users.auth import get_current_active_user
from users.models import User, UserRole

# `/manager` va boshqa ichki (xodimlar uchun) bo'limlarga kira oladigan rollar.
# Bu MOLIYA huquqi EMAS — moliya faqat `is_admin_user` orqali.
STAFF_ROLES: frozenset[UserRole] = frozenset({UserRole.ADMIN, UserRole.MANAGER})


def is_admin_user(user: User) -> bool:
    """Admin huquqi — moliya, sozlamalar, foydalanuvchilarni boshqarish.

    `ADMIN_IDS` (.env dagi `ADMIN`) tarixiy sabab bilan saqlanadi: bazadagi roli
    hali `admin` bo'lmagan asoschi hisoblar ham panelga kira olishi kerak.
    """
    return user.role == UserRole.ADMIN or user.id in ADMIN_IDS


def is_staff(user: User) -> bool:
    """Ichki xodim (admin yoki manager) — buyurtmalarni operativ boshqarish huquqi."""
    return is_admin_user(user) or user.role in STAFF_ROLES


def is_manager(user: User) -> bool:
    """Aynan MANAGER (admin emas) — moliya maydonlarini tozalash uchun kerak.

    Admin bir vaqtning o'zida manager emas: admin narxni ko'rishda davom etadi.
    """
    return user.role == UserRole.MANAGER and not is_admin_user(user)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_roles(*roles: UserRole, detail: str | None = None) -> Callable:
    """Dependency fabrikasi: sanab o'tilgan rollardan biri bo'lsa o'tkazadi.

    `get_current_active_user` ustiga quriladi — banlangan/nofaol akkaunt tekshiruvi
    (`users/auth.py:110`) tekin keladi, uni har joyda takrorlash shart emas.

    Ishlatilishi:
        @router.get("/x", dependencies=[Depends(require_roles(UserRole.DRIVER))])
    yoki foydalanuvchi obyekti kerak bo'lsa:
        user: User = Depends(require_roles(UserRole.DRIVER))
    """
    allowed = frozenset(roles)
    message = detail or (
        "Bu amal uchun huquqingiz yo'q. Kerakli rol: "
        + ", ".join(sorted(r.value for r in allowed))
    )

    async def _dependency(current_user: User = Depends(get_current_active_user)) -> User:
        # Admin barcha rol tekshiruvlaridan o'tadi — bu ATAYLAB emas: agar admin
        # avtomatik o'tsa, "faqat sender o'z buyurtmasini tahrirlaydi" kabi qoidalar
        # buzilardi. Shuning uchun admin ham ro'yxatda ko'rsatilishi kerak.
        if current_user.role in allowed:
            return current_user
        if UserRole.ADMIN in allowed and current_user.id in ADMIN_IDS:
            return current_user
        raise _forbidden(message)

    return _dependency


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Admin (moliya va tizim sozlamalari uchun). `Admin_panel.validation.is_admin` shu yerga tayanadi."""
    if is_admin_user(current_user):
        return current_user
    raise _forbidden("Sizda ushbu amalni bajarish uchun huquq yo'q (Admin emassiz)!")


async def get_current_manager(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Aynan manager."""
    if current_user.role == UserRole.MANAGER:
        return current_user
    raise _forbidden("Bu bo'lim faqat menejerlar uchun.")


async def get_current_staff(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Admin yoki manager — `/manager` router'i shu bilan himoyalangan.

    DIQQAT: bu dependency MOLIYAGA ruxsat bermaydi. Moliyaviy endpointlar
    `get_current_admin_user` / `Admin_panel.validation.is_admin` bilan qoladi.
    """
    if is_staff(current_user):
        return current_user
    raise _forbidden("Bu bo'lim faqat admin va menejerlar uchun.")


def role_names(roles: Iterable[UserRole]) -> list[str]:
    """Xato matnlari va testlar uchun kichik yordamchi."""
    return sorted(r.value for r in roles)
