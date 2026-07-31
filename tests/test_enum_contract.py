"""Enum shartnomasi: Python ↔ PostgreSQL ↔ frontend qiymatlari bir xil ekanini qulflaydi.

Nega kerak: `orders.status` va `order_waypoints.status`/`type` ustunlari PostgreSQL
enum tiplariga bog'langan. Python tomonida a'zo nomini yoki qiymatini o'zgartirish
migratsiyasiz bazadagi tip bilan mos kelmay qoladi va so'rovlar ishlamay boshlaydi —
bunday xato ishga tushirish paytida emas, faqat foydalanuvchi tugmani bosganda
ko'rinadi. Bu testlar shu farqni darhol ushlaydi.

Quyidagi ro'yxatlar — bazadagi HAQIQIY qiymatlar (`\\dT+` chiqishi bilan tekshirilgan).
Ularni o'zgartirish faqat mos alembic migratsiyasi bilan birga qilinishi kerak.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from order.dispatch_models import DispatchAttemptStatus, DispatchMatchType
from order.models import Order, OrderStatus, OrderWaypoint, WaypointStatus, WaypointType

# ── Bazadagi enum tiplari va ularning qiymatlari ────────────────────────────
DB_ENUMS: dict[str, tuple[type, list[str]]] = {
    "orderstatus": (
        OrderStatus,
        ["SCHEDULED", "PENDING", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
    ),
    "waypointstatus": (WaypointStatus, ["PENDING", "ARRIVED", "COMPLETED", "SKIPPED"]),
    "waypointtype": (WaypointType, ["PICKUP", "DELIVERY", "TRANSIT"]),
    # Dispatch tiplari ATAYLAB kichik harflarda — ular ham shu qoidaga bo'ysunadi.
    "dispatchattemptstatus": (
        DispatchAttemptStatus,
        ["pending", "accepted", "rejected", "expired", "cancelled"],
    ),
    "dispatchmatchtype": (DispatchMatchType, ["gps", "region"]),
}

FRONTEND_TYPES = Path(__file__).resolve().parent.parent / "Frontend" / "src" / "types" / "api.ts"


@pytest.mark.parametrize("type_name", sorted(DB_ENUMS))
def test_python_enum_values_match_database(type_name):
    """Python enum QIYMATLARI bazadagi label'lar bilan aynan bir xil (registrgacha)."""
    enum_cls, expected = DB_ENUMS[type_name]
    assert [member.value for member in enum_cls] == expected


@pytest.mark.parametrize("type_name", sorted(DB_ENUMS))
def test_enum_membership_is_case_exact(type_name):
    """`WaypointStatus("ARRIVED")` ishlaydi, `("arrived")` esa YO'Q.

    Registrga chidamlilik faqat kirish sxemasida (`WaypointProgressUpdate`) qo'shilgan —
    enum'ning o'zi qat'iy bo'lib qolishi kerak, aks holda bazaga noto'g'ri yozuv tushardi.
    """
    enum_cls, expected = DB_ENUMS[type_name]
    for value in expected:
        assert enum_cls(value).value == value
        with pytest.raises(ValueError):
            enum_cls(value.swapcase())


@pytest.mark.parametrize(
    ("column", "type_name"),
    [
        (Order.__table__.c.status, "orderstatus"),
        (OrderWaypoint.__table__.c.status, "waypointstatus"),
        (OrderWaypoint.__table__.c.type, "waypointtype"),
    ],
)
def test_sqlalchemy_column_sends_values_not_names(column, type_name):
    """Ustun bazaga a'zo NOMINI emas, QIYMATINI yuboradi (`values_callable`).

    Hozir nom va qiymat bir xil, shuning uchun xato ko'rinmasdi — lekin kimdir
    `ARRIVED = "arrived"` deb yozsa, `values_callable`siz ustun bazaga "ARRIVED"
    yuborib, `invalid input value for enum` bilan yiqilardi.
    """
    db_type = column.type
    assert db_type.name == type_name
    assert db_type.enums == DB_ENUMS[type_name][1]


def _ts_union_values(source: str, type_name: str) -> list[str]:
    """`export type X = 'A' | 'B';` qatoridan qiymatlarni ajratib oladi."""
    match = re.search(rf"export type {type_name} =([^;]+);", source)
    assert match, f"Frontend tipida {type_name} topilmadi: {FRONTEND_TYPES}"
    return re.findall(r"'([^']+)'", match.group(1))


@pytest.mark.parametrize(
    ("ts_type", "type_name"),
    [
        ("OrderStatus", "orderstatus"),
        ("WaypointStatus", "waypointstatus"),
        ("WaypointType", "waypointtype"),
    ],
)
def test_frontend_union_matches_database(ts_type, type_name):
    """WebApp'dagi TypeScript union bazadagi qiymatlar bilan bir xil.

    Frontend bu qiymatlarni ham yuboradi (`PATCH .../waypoints/{id}`), ham javobda
    solishtiradi (`status === 'COMPLETED'`) — bitta harf farq qilsa ekran jimgina
    noto'g'ri holat ko'rsatardi.
    """
    values = _ts_union_values(FRONTEND_TYPES.read_text(encoding="utf-8"), ts_type)
    assert values == DB_ENUMS[type_name][1]


def test_openapi_exposes_exact_enum_values():
    """OpenAPI sxemasida ham aynan shu qiymatlar — tashqi integratsiyalar uchun manba."""
    from config.main import app

    schema = json.loads(json.dumps(app.openapi()))
    status_prop = schema["components"]["schemas"]["WaypointProgressUpdate"]["properties"]["status"]

    # Pydantic versiyasiga qarab enum havolasi to'g'ridan-to'g'ri `$ref` yoki
    # `allOf: [{$ref: ...}]` shaklida chiqadi — ikkalasi ham qo'llab-quvvatlanadi.
    ref = status_prop.get("$ref") or status_prop["allOf"][0]["$ref"]
    enum_name = ref.rsplit("/", 1)[-1]
    assert schema["components"]["schemas"][enum_name]["enum"] == DB_ENUMS["waypointstatus"][1]
