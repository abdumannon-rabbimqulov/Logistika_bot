"""Haqiqiy FastAPI ilovasi orqali menejer chegaralari (HTTP darajasi).

`tests/test_manager_permissions.py` funksiyalarni alohida tekshiradi — bu esa butun
zanjirni: router → dependency → 403. Farqi muhim, chunki huquq teshigi odatda
funksiyada emas, uni ULASHNI unutishda paydo bo'ladi (masalan yangi endpointga
`Depends(is_admin)` yozilmay qolsa).

Baza kerak emas: `get_current_user` va `get_db` almashtiriladi. `get_db` bo'sh
sessiya beradi, shuning uchun ruxsat berilgan endpoint DB ga yetganda 500 bilan
yiqiladi — test aynan "403 EMAS" ni tekshiradi, ya'ni ruxsat berilganini.

`config.main` import qilinishi uchun `.env` (BOT_TOKEN, SECRET_KEY, DB_URL) kerak;
bo'lmasa test o'tkazib yuboriladi.
"""

from __future__ import annotations

import pytest

from users.models import User, UserRole

app_module = pytest.importorskip(
    "config.main", reason="config.main import uchun .env (BOT_TOKEN/SECRET_KEY/DB_URL) kerak"
)

from fastapi.testclient import TestClient  # noqa: E402

from config.config import get_db  # noqa: E402
from users.auth import get_current_user  # noqa: E402

# Moliyaviy va admin endpointlar — menejer uchun HAMMASI yopiq bo'lishi kerak.
FINANCE_ENDPOINTS = [
    ("GET", "/system/users/5/balance/transactions", None),
    ("POST", "/system/users/5/balance/adjust", {"amount": 1000, "reason": "test"}),
    ("GET", "/system/settings/commission", None),
    ("GET", "/system/settings/pricing", None),
    ("GET", "/system/dashboard/stats", None),
    ("GET", "/system/users", None),
    ("GET", "/system/orders", None),
]

MANAGER_ENDPOINTS = [
    ("GET", "/manager/orders", None),
    ("GET", "/manager/orders/1", None),
    ("GET", "/manager/orders/1/available-trucks", None),
]


@pytest.fixture
def client():
    app = app_module.app
    holder: dict[str, User] = {}

    async def _current_user():
        return holder["user"]

    async def _db():
        yield None

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_db] = _db

    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.login_as = lambda role: holder.update(  # type: ignore[attr-defined]
        user=User(id=501, role=role, is_active=True, is_banned=False)
    )
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("method,path,body", FINANCE_ENDPOINTS)
def test_manager_is_blocked_from_finance_and_admin(client, method, path, body):
    client.login_as(UserRole.MANAGER)
    response = client.request(method, path, json=body)
    assert response.status_code == 403, (
        f"{method} {path} menejerga ochiq qolgan (status {response.status_code}) — "
        "moliya bo'limi menejerdan to'liq yopiq bo'lishi kerak"
    )


@pytest.mark.parametrize("method,path,body", FINANCE_ENDPOINTS)
def test_admin_still_reaches_finance(client, method, path, body):
    """Nazorat testi: blok ADMIN uchun ham yopilib qolmasin."""
    client.login_as(UserRole.ADMIN)
    response = client.request(method, path, json=body)
    assert response.status_code != 403


@pytest.mark.parametrize("method,path,body", MANAGER_ENDPOINTS)
def test_manager_reaches_manager_panel(client, method, path, body):
    client.login_as(UserRole.MANAGER)
    response = client.request(method, path, json=body)
    assert response.status_code != 403


@pytest.mark.parametrize("role", [UserRole.SENDER, UserRole.DRIVER, UserRole.GUEST])
@pytest.mark.parametrize("method,path,body", MANAGER_ENDPOINTS)
def test_manager_panel_closed_for_regular_roles(client, role, method, path, body):
    client.login_as(role)
    response = client.request(method, path, json=body)
    assert response.status_code == 403


def test_manager_cannot_use_admin_only_order_endpoints(client):
    """Menejer buyurtma statusini `/orders/{id}/status` orqali o'zgartira olmaydi —
    unga `/manager/orders/{id}/status` berilgan. `/orders/{id}/assign-driver` ham admin uchun."""
    client.login_as(UserRole.MANAGER)
    assert client.post("/orders/1/assign-driver", json={"driver_id": 3}).status_code == 403
