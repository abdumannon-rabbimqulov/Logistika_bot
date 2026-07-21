"""Avtomatik dispatch tizimi: dispatch_attempts jadvali va orders'ga yangi ustunlar

Bu loyihada ilgari alembic migratsiya tarixi umuman yozilmagan edi (jadvallar faqat
`Base.metadata.create_all` orqali yaratilgan, `config/main.py`). Shu sababli bu revizyaga
`down_revision = None` qo'yilgan — mavjud (ilgari yaratilgan) jadvallarni qayta yaratishga
urinmaydi, faqat shu ishda qo'shilgan yangi narsalarni qo'shadi:
- `dispatch_attempts` jadvali (agar mavjud bo'lmasa — `create_all` ham buni yaratadi,
  lekin aniqlik/production uchun bu yerda ham bor, `IF NOT EXISTS` bilan xavfsiz)
- `orders` jadvaliga 4 ta yangi ustun (hammasi nullable/default bilan — mavjud qatorlarga
  ta'sir qilmaydi)

Revision ID: 8b1137822e41
Revises:
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b1137822e41"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "dispatch_attempts" not in existing_tables:
        op.create_table(
            "dispatch_attempts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("round_number", sa.SmallInteger(), nullable=False),
            sa.Column(
                "match_type",
                sa.Enum("gps", "region", name="dispatchmatchtype"),
                nullable=False,
            ),
            sa.Column("distance_km", sa.Numeric(6, 2), nullable=True),
            sa.Column(
                "status",
                sa.Enum("pending", "accepted", "rejected", "expired", "cancelled", name="dispatchattemptstatus"),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("bot_chat_id", sa.BigInteger(), nullable=True),
            sa.Column("bot_message_id", sa.BigInteger(), nullable=True),
        )
        op.create_index("ix_dispatch_attempts_order_status", "dispatch_attempts", ["order_id", "status"])
        op.create_index("ix_dispatch_attempts_driver_status", "dispatch_attempts", ["driver_id", "status"])
        op.create_index("ix_dispatch_attempts_expires_at", "dispatch_attempts", ["expires_at"])

    orders_columns = {col["name"] for col in inspector.get_columns("orders")} if "orders" in existing_tables else set()

    if "dispatch_round" not in orders_columns:
        op.add_column(
            "orders",
            sa.Column("dispatch_round", sa.Integer(), nullable=False, server_default="0"),
        )
    if "original_price" not in orders_columns:
        op.add_column("orders", sa.Column("original_price", sa.Numeric(12, 2), nullable=True))
    if "price_bump_requested_at" not in orders_columns:
        op.add_column("orders", sa.Column("price_bump_requested_at", sa.DateTime(timezone=True), nullable=True))
    if "overload_warning" not in orders_columns:
        op.add_column("orders", sa.Column("overload_warning", sa.String(300), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "overload_warning")
    op.drop_column("orders", "price_bump_requested_at")
    op.drop_column("orders", "original_price")
    op.drop_column("orders", "dispatch_round")

    op.drop_index("ix_dispatch_attempts_expires_at", table_name="dispatch_attempts")
    op.drop_index("ix_dispatch_attempts_driver_status", table_name="dispatch_attempts")
    op.drop_index("ix_dispatch_attempts_order_status", table_name="dispatch_attempts")
    op.drop_table("dispatch_attempts")

    bind = op.get_bind()
    sa.Enum(name="dispatchattemptstatus").drop(bind, checkfirst=True)
    sa.Enum(name="dispatchmatchtype").drop(bind, checkfirst=True)
