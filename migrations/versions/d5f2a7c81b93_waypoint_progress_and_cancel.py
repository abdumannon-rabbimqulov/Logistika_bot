"""order_waypoints qadam/GPS ustunlari + orders bekor qilish ustunlari

Waypoint holatlari (PENDING/ARRIVED/COMPLETED) shu paytgacha o'lik edi — hech kim
yozmasdi. Endi haydovchi har bir nuqtada "Yetib keldim" / "Yukni ortdim" bosadi va
har bir qadam GPS bilan tekshiriladi. Tekshiruv natijasi (haydovchining haqiqiy
koordinatasi, o'lchangan masofa, GPS aniqligi) audit uchun saqlanadi — nizo
holatida "haydovchi rostdan ham nuqtada edimi?" degan savolga javob beradi.

`override_by_user_id`/`override_reason` — GPS nosoz bo'lganda admin qo'lda
tasdiqlashi mumkin; to'ldirilgan bo'lsa bu qadam geofence'dan o'tmagani bildiradi.

`orders.cancelled_*` — bekor qilish endi qattiq DELETE emas, CANCELLED statusi.

DIQQAT — ma'lumot ko'chirish: hozir `IN_PROGRESS` holatidagi buyurtmalarning barcha
nuqtalari `PENDING` bo'lib turibdi. Yangi oqim birinchi tugallanmagan nuqtadan
boshlanadi, shuning uchun bunday buyurtmalarda haydovchi yukni ikkinchi marta
"ortishga" majbur bo'lardi. Shu sabab ular uchun yuk ortish nuqtasi (eng kichik
`sequence`) COMPLETED deb belgilanadi. `COMPLETED` buyurtmalarda esa barcha
nuqtalar yopiladi — aks holda admin paneldagi progress bar yakunlangan yukda ham
0% ko'rsatib turaveradi.

Revision ID: d5f2a7c81b93
Revises: c3a91d47f052
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5f2a7c81b93"
down_revision: Union[str, Sequence[str], None] = "c3a91d47f052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (ustun nomi, tur) — jadval `Base.metadata.create_all` orqali yaratilgani uchun
# har bir ustun mavjudligi alohida tekshiriladi (idempotent, qayta ishga tushirsa ham xavfsiz).
_WAYPOINT_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("arrived_at", sa.DateTime(timezone=True)),
    ("completed_at", sa.DateTime(timezone=True)),
    ("confirmed_latitude", sa.Float()),
    ("confirmed_longitude", sa.Float()),
    ("confirmed_distance_m", sa.Integer()),
    ("confirmed_accuracy_m", sa.Integer()),
    ("override_by_user_id", sa.BigInteger()),
    ("override_reason", sa.String(length=300)),
]

_ORDER_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("cancelled_at", sa.DateTime(timezone=True)),
    ("cancelled_by_user_id", sa.BigInteger()),
    ("cancel_reason", sa.String(length=300)),
]


def _add_missing(table: str, columns: list[tuple[str, sa.types.TypeEngine]]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {col["name"] for col in inspector.get_columns(table)}
    for name, type_ in columns:
        if name not in existing:
            op.add_column(table, sa.Column(name, type_, nullable=True))


def _drop_existing(table: str, columns: list[tuple[str, sa.types.TypeEngine]]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {col["name"] for col in inspector.get_columns(table)}
    for name, _ in columns:
        if name in existing:
            op.drop_column(table, name)


def upgrade() -> None:
    """Upgrade schema."""
    _add_missing("order_waypoints", _WAYPOINT_COLUMNS)
    _add_missing("orders", _ORDER_COLUMNS)

    # Foreign key'lar ustunlar qo'shilgandan keyin, alohida va nom bilan —
    # takroriy ishga tushirishda nomi bo'yicha borligini tekshirish mumkin bo'lsin.
    inspector = sa.inspect(op.get_bind())

    wp_fks = {fk.get("name") for fk in inspector.get_foreign_keys("order_waypoints")}
    if "fk_order_waypoints_override_by_user_id" not in wp_fks:
        op.create_foreign_key(
            "fk_order_waypoints_override_by_user_id",
            "order_waypoints", "users",
            ["override_by_user_id"], ["id"], ondelete="SET NULL",
        )

    order_fks = {fk.get("name") for fk in inspector.get_foreign_keys("orders")}
    if "fk_orders_cancelled_by_user_id" not in order_fks:
        op.create_foreign_key(
            "fk_orders_cancelled_by_user_id",
            "orders", "users",
            ["cancelled_by_user_id"], ["id"], ondelete="SET NULL",
        )

    # ── Ma'lumot ko'chirish (yuqoridagi izohga qarang) ──────────────────────────
    # Yo'ldagi buyurtmalar: yuk allaqachon ortilgan, shuning uchun eng kichik
    # sequence'li nuqta yopiladi. `completed_at` uchun ishonchli vaqt yo'q —
    # buyurtmaning `updated_at` i eng yaqin taxmin.
    op.execute(
        """
        UPDATE order_waypoints wp
           SET status = 'COMPLETED',
               arrived_at = COALESCE(wp.arrived_at, o.updated_at),
               completed_at = COALESCE(wp.completed_at, o.updated_at)
          FROM orders o
         WHERE wp.order_id = o.id
           AND o.status = 'IN_PROGRESS'
           AND wp.status = 'PENDING'
           AND wp.sequence = (
               SELECT MIN(w2.sequence) FROM order_waypoints w2 WHERE w2.order_id = o.id
           )
        """
    )

    # Yakunlangan buyurtmalar: barcha nuqtalar yopilgan bo'lishi kerak.
    op.execute(
        """
        UPDATE order_waypoints wp
           SET status = 'COMPLETED',
               arrived_at = COALESCE(wp.arrived_at, o.completed_at, o.updated_at),
               completed_at = COALESCE(wp.completed_at, o.completed_at, o.updated_at)
          FROM orders o
         WHERE wp.order_id = o.id
           AND o.status = 'COMPLETED'
           AND wp.status = 'PENDING'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())

    if "fk_order_waypoints_override_by_user_id" in {
        fk.get("name") for fk in inspector.get_foreign_keys("order_waypoints")
    }:
        op.drop_constraint(
            "fk_order_waypoints_override_by_user_id", "order_waypoints", type_="foreignkey"
        )
    if "fk_orders_cancelled_by_user_id" in {
        fk.get("name") for fk in inspector.get_foreign_keys("orders")
    }:
        op.drop_constraint("fk_orders_cancelled_by_user_id", "orders", type_="foreignkey")

    _drop_existing("order_waypoints", _WAYPOINT_COLUMNS)
    _drop_existing("orders", _ORDER_COLUMNS)
