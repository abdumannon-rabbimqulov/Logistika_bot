"""Dispatch navbati: price_bump_count, last_dispatch_enqueued_at

Haydovchi qidirish endi RabbitMQ navbati orqali fon jarayonida bajariladi
(`workers/dispatch_worker.py`). Shu bilan bog'liq ikkita ustun:

- `orders.price_bump_count` — sender narxni necha marta oshirgani. Cheklov
  (`services/dispatch.py MAX_PRICE_BUMPS`) haydovchisiz yo'nalishda "oshir →
  topilmadi → yana oshir" siklining cheksiz aylanishini to'xtatadi.
- `orders.last_dispatch_enqueued_at` — qidiruv vazifasi oxirgi marta navbatga
  qo'yilgan payt. Broker o'chgan paytda qo'yilmay qolgan buyurtmalarni davriy
  sweep (`requeue_stuck_orders`) aynan shu ustun bo'yicha topadi.

Mavjud buyurtmalarda `price_bump_count` 0 bo'ladi (server_default), ya'ni ular
uchun limit noldan boshlanadi; `last_dispatch_enqueued_at` esa NULL qoladi va
birinchi sweep'da qidiruvga qaytariladi.

Revision ID: e9d3f0c85a21
Revises: a7c4e91b2d10
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9d3f0c85a21"
down_revision: Union[str, Sequence[str], None] = "a7c4e91b2d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    order_columns = {col["name"] for col in inspector.get_columns("orders")}

    if "price_bump_count" not in order_columns:
        op.add_column(
            "orders",
            sa.Column(
                "price_bump_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if "last_dispatch_enqueued_at" not in order_columns:
        op.add_column(
            "orders",
            sa.Column("last_dispatch_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        )

    # `requeue_stuck_orders` har 20 soniyada shu shart bo'yicha qidiradi — PENDING
    # buyurtmalar uchun qisman indeks (jadval o'sganda ham skan arzon qoladi).
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("orders")}
    if "ix_orders_pending_dispatch" not in existing_indexes:
        op.create_index(
            "ix_orders_pending_dispatch",
            "orders",
            ["last_dispatch_enqueued_at"],
            postgresql_where=sa.text("status = 'PENDING' AND driver_id IS NULL"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("orders")}
    if "ix_orders_pending_dispatch" in existing_indexes:
        op.drop_index("ix_orders_pending_dispatch", table_name="orders")

    order_columns = {col["name"] for col in inspector.get_columns("orders")}
    if "last_dispatch_enqueued_at" in order_columns:
        op.drop_column("orders", "last_dispatch_enqueued_at")
    if "price_bump_count" in order_columns:
        op.drop_column("orders", "price_bump_count")
