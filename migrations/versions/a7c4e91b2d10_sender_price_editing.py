"""Sender narx tahriri: base_price, billable_distance_km, sender_max_discount_percent

Yangi biznes qoidalari:

- Narx 5 km qadamiga yaxlitlangan masofadan hisoblanadi — hisobda ishlatilgan
  masofa `orders.billable_distance_km` ga yoziladi (`total_distance_km` esa OSRM
  bergan aniq masofa bo'lib qoladi).
- Sender narxni qo'lda tahrirlay oladi. Chegirma chegarasi tizim hisoblagan
  `orders.base_price` dan hisoblanadi, foiz esa
  `platform_settings.sender_max_discount_percent` (standart 15%) da saqlanadi.

Mavjud buyurtmalarda `base_price` joriy `price` bilan to'ldiriladi (u paytda narx
hali qo'lda tahrirlanmagan edi), `billable_distance_km` esa NULL qoladi.

Revision ID: a7c4e91b2d10
Revises: d5f2a7c81b93
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c4e91b2d10"
down_revision: Union[str, Sequence[str], None] = "d5f2a7c81b93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    order_columns = {col["name"] for col in inspector.get_columns("orders")}
    if "base_price" not in order_columns:
        op.add_column("orders", sa.Column("base_price", sa.Numeric(12, 2), nullable=True))
        op.execute("UPDATE orders SET base_price = price WHERE base_price IS NULL")
    if "billable_distance_km" not in order_columns:
        op.add_column("orders", sa.Column("billable_distance_km", sa.Integer(), nullable=True))

    settings_columns = {col["name"] for col in inspector.get_columns("platform_settings")}
    if "sender_max_discount_percent" not in settings_columns:
        op.add_column(
            "platform_settings",
            sa.Column(
                "sender_max_discount_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="15.00",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("platform_settings", "sender_max_discount_percent")
    op.drop_column("orders", "billable_distance_km")
    op.drop_column("orders", "base_price")
