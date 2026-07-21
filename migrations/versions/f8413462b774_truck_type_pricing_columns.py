"""Truck type narxlash ustunlari (base_price/price_per_km/min_price) — DB'da yo'q edi

Model (`driver/models.py` `TruckType`) bu ustunlarni allaqachon e'lon qiladi (narxlash
ishi qo'shilganda), lekin loyihada bu paytgacha haqiqiy migratsiya bo'lmagani va
faqat `Base.metadata.create_all()` ishlatilgani sabab (u faqat YO'Q jadvallarni
yaratadi, mavjud jadvalga ustun qo'shmaydi) — `truck_types` jadvali eski holida
qolib ketgan edi. `GET /drivers/truck-types` va order narxini hisoblash shu sabab
`UndefinedColumnError` bilan ishlamay qolgan.

Revision ID: f8413462b774
Revises: bb726de280e6
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8413462b774"
down_revision: Union[str, Sequence[str], None] = "bb726de280e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("truck_types")}

    if "base_price" not in columns:
        op.add_column(
            "truck_types",
            sa.Column("base_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        )
    if "price_per_km" not in columns:
        op.add_column(
            "truck_types",
            sa.Column("price_per_km", sa.Numeric(12, 2), nullable=False, server_default="0"),
        )
    if "min_price" not in columns:
        op.add_column("truck_types", sa.Column("min_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("truck_types", "min_price")
    op.drop_column("truck_types", "price_per_km")
    op.drop_column("truck_types", "base_price")
