"""Manager rolining huquq chegaralari.

Bu testlar aynan bitta narsani qulflaydi: MENEJER MOLIYAGA KIRA OLMAYDI.
`Admin_panel/router.py` dagi barcha balans/komissiya endpointlari
`Admin_panel.validation.is_admin` ga tayanadi, u esa `is_admin_user` ni chaqiradi —
shuning uchun shu funksiyaning menejerni rad etishi butun moliya bo'limining
yopiqligini bildiradi. Agar kimdir ertaga `is_admin_user` ga `MANAGER` ni qo'shsa,
moliya jimgina ochilib ketardi; test buni darhol ushlaydi.

Baza kerak emas: `User` obyekti xotirada yaratiladi (`tests/conftest.py` mapper'larni
allaqachon sozlab qo'ygan).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from users import permissions
from users.models import User, UserRole


def make_user(role: UserRole, user_id: int = 1000) -> User:
    return User(id=user_id, role=role, is_active=True, is_banned=False)


ALL_ROLES = [
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.SENDER,
    UserRole.DRIVER,
    UserRole.GUEST,
    UserRole.DISPATCHER,
]


# ── Moliya chegarasi ────────────────────────────────────────────────────────

def test_manager_is_not_admin():
    """Eng muhim tekshiruv: menejer admin emas → `/system` (moliya) yopiq."""
    assert permissions.is_admin_user(make_user(UserRole.MANAGER)) is False


@pytest.mark.parametrize("role", [r for r in ALL_ROLES if r is not UserRole.ADMIN])
def test_only_admin_role_gets_admin_rights(role):
    assert permissions.is_admin_user(make_user(role)) is False


def test_admin_role_gets_admin_rights():
    assert permissions.is_admin_user(make_user(UserRole.ADMIN)) is True


def test_admin_ids_env_still_grants_admin(monkeypatch):
    """`.env` dagi ADMIN ro'yxati tarixiy sabab bilan saqlanadi — buzilmasin."""
    monkeypatch.setattr(permissions, "ADMIN_IDS", {777})
    assert permissions.is_admin_user(make_user(UserRole.SENDER, user_id=777)) is True


# ── Xodim (staff) chegarasi ────────────────────────────────────────────────

@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.MANAGER])
def test_staff_includes_admin_and_manager(role):
    assert permissions.is_staff(make_user(role)) is True


@pytest.mark.parametrize(
    "role", [UserRole.SENDER, UserRole.DRIVER, UserRole.GUEST, UserRole.DISPATCHER]
)
def test_staff_excludes_everyone_else(role):
    assert permissions.is_staff(make_user(role)) is False


def test_is_manager_excludes_admin():
    """`is_manager` narx tozalash uchun ishlatiladi — admin narxni ko'rishda davom etadi."""
    assert permissions.is_manager(make_user(UserRole.MANAGER)) is True
    assert permissions.is_manager(make_user(UserRole.ADMIN)) is False


def test_is_manager_false_for_manager_listed_in_admin_ids(monkeypatch):
    """`.env` da admin deb ko'rsatilgan hisob menejer sifatida tozalanmaydi."""
    monkeypatch.setattr(permissions, "ADMIN_IDS", {42})
    assert permissions.is_manager(make_user(UserRole.MANAGER, user_id=42)) is False


# ── Dependency'lar ─────────────────────────────────────────────────────────

async def test_get_current_staff_allows_manager():
    user = make_user(UserRole.MANAGER)
    assert await permissions.get_current_staff(user) is user


async def test_get_current_staff_rejects_sender():
    with pytest.raises(HTTPException) as exc:
        await permissions.get_current_staff(make_user(UserRole.SENDER))
    assert exc.value.status_code == 403


async def test_get_current_admin_user_rejects_manager():
    """Moliya endpointlari shu dependency orqali himoyalangan."""
    with pytest.raises(HTTPException) as exc:
        await permissions.get_current_admin_user(make_user(UserRole.MANAGER))
    assert exc.value.status_code == 403


async def test_get_current_manager_rejects_admin():
    with pytest.raises(HTTPException) as exc:
        await permissions.get_current_manager(make_user(UserRole.ADMIN))
    assert exc.value.status_code == 403


async def test_require_roles_factory():
    dependency = permissions.require_roles(UserRole.DRIVER, UserRole.SENDER)

    driver = make_user(UserRole.DRIVER)
    assert await dependency(driver) is driver

    with pytest.raises(HTTPException) as exc:
        await dependency(make_user(UserRole.MANAGER))
    assert exc.value.status_code == 403


async def test_require_roles_does_not_auto_admit_admin():
    """Admin ro'yxatda bo'lmasa o'tmasligi kerak — aks holda "faqat egasi"
    qoidalari admin uchun jimgina buzilardi."""
    dependency = permissions.require_roles(UserRole.SENDER)
    with pytest.raises(HTTPException):
        await dependency(make_user(UserRole.ADMIN))
