"""`OrderFlowError` → 400 Bad Request (500 emas).

Muammo: `OrderFlowError` tutib olinmagan joyda ko'tarilsa (masalan
`Admin_panel/router.py` dagi status o'zgartirish — u yerda `try/except` yo'q edi),
`middlewares/error_handler.py` dagi umumiy `Exception` handleriga tushib, mijozga
**500 Internal Server Error** qaytarardi. Holbuki bu server nosozligi emas — mijoz
qoidaga zid o'tish so'ragan.

Endi maxsus handler ro'yxatdan o'tgan va har qanday joydagi `OrderFlowError` 400
bo'lib qaytadi.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middlewares.error_handler import setup_error_handlers
from order.models import OrderStatus
from services import order_flow
from services.order_flow import OrderFlowError, OrderTransitionError


@pytest.fixture
def client() -> TestClient:
    """Handlerlar o'rnatilgan mini-ilova: endpointlar xatoni TUTMAYDI."""
    app = FastAPI()
    setup_error_handlers(app)

    @app.patch("/status")
    def change_status(current: str, new: str):
        order_flow.ensure_order_transition_allowed(OrderStatus(current), OrderStatus(new))
        return {"ok": True}

    @app.post("/generic")
    def generic():
        raise OrderFlowError("Buyurtmaning barcha nuqtalari allaqachon yakunlangan.")

    @app.get("/boom")
    def boom():
        raise RuntimeError("haqiqiy nosozlik")

    return TestClient(app, raise_server_exceptions=False)


# ────────────────────────────────────────────────────────────
#  1. Status o'tishi — 400 va aniq xabar
# ────────────────────────────────────────────────────────────

def test_invalid_transition_returns_400(client):
    """Regressiya: ilgari bu yo'l 500 berardi."""
    response = client.patch("/status", params={"current": "ACCEPTED", "new": "COMPLETED"})
    assert response.status_code == 400


def test_invalid_transition_message(client):
    response = client.patch("/status", params={"current": "ACCEPTED", "new": "COMPLETED"})
    message = response.json()["detail"]["message"]

    # Talab qilingan matn: holatlar o'zbekcha yorliq bilan + ketma-ketlik eslatmasi
    assert message == (
        "'qabul qilingan' holatidan 'yakunlangan' holatiga o'tish mumkin emas. "
        "Iltimos, statuslarni ketma-ketlikda o'zgartiring."
    )


def test_invalid_transition_context(client):
    """Xom enum qiymatlari va ruxsat etilgan variantlar ham qaytadi."""
    response = client.patch("/status", params={"current": "ACCEPTED", "new": "COMPLETED"})
    error = response.json()["detail"]["errors"][0]

    assert error["code"] == "INVALID_ORDER_TRANSITION"
    assert error["current_status"] == "ACCEPTED"
    assert error["new_status"] == "COMPLETED"
    # ACCEPTED dan faqat shu ikkisiga o'tish mumkin — mijoz to'g'ri qadamni tanlay oladi
    assert error["allowed_statuses"] == ["CANCELLED", "IN_PROGRESS"]


def test_terminal_status_has_no_allowed_transitions(client):
    response = client.patch("/status", params={"current": "COMPLETED", "new": "PENDING"})
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["allowed_statuses"] == []


def test_allowed_transition_passes(client):
    assert client.patch("/status", params={"current": "ACCEPTED", "new": "IN_PROGRESS"}).status_code == 200


def test_same_status_is_noop(client):
    """Bir xil holatga "o'tish" xato emas — takroriy so'rov bloklanmasligi kerak."""
    assert client.patch("/status", params={"current": "ACCEPTED", "new": "ACCEPTED"}).status_code == 200


# ────────────────────────────────────────────────────────────
#  2. Boshqa OrderFlowError lar ham 400
# ────────────────────────────────────────────────────────────

def test_generic_order_flow_error_is_400(client):
    """Status o'tishi bilan bog'liq bo'lmagan qoida buzilishi ham 400 bo'ladi."""
    response = client.post("/generic")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["message"] == "Buyurtmaning barcha nuqtalari allaqachon yakunlangan."
    assert detail["errors"][0]["code"] == "ORDER_FLOW_ERROR"


def test_real_failure_is_still_500(client):
    """Muhim: handler haqiqiy nosozliklarni yashirib qo'ymasligi kerak."""
    assert client.get("/boom").status_code == 500


# ────────────────────────────────────────────────────────────
#  3. Istisno turlari
# ────────────────────────────────────────────────────────────

def test_transition_error_is_order_flow_error():
    """Eski `except OrderFlowError` bloklari ishlashda davom etadi."""
    assert issubclass(OrderTransitionError, OrderFlowError)


def test_transition_error_carries_statuses():
    exc = OrderTransitionError(OrderStatus.PENDING, OrderStatus.COMPLETED)

    assert exc.current == OrderStatus.PENDING
    assert exc.new == OrderStatus.COMPLETED
    assert exc.context()["current_status"] == "PENDING"
    assert "o'tish mumkin emas" in str(exc)


def test_handler_registered_on_real_app():
    """Haqiqiy ilovada ham handler o'rnatilgan (mini-ilovada emas)."""
    from config.main import app

    assert OrderFlowError in app.exception_handlers
