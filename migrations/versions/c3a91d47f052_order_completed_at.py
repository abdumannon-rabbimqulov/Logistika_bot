"""orders.completed_at — buyurtma yakunlangan payt

Haydovchi kabinetidagi daromad hisoboti (Frontend `DriverEarningsPage`) haftalik
guruhlashni shu ustun bo'yicha qiladi. Ilgari `created_at` ishlatilgan edi — bu
noto'g'ri: 10 kun oldin yaratilib bugun yakunlangan yuk "shu hafta" daromadiga
umuman tushmasdi, bugun yaratilib keyingi hafta yakunlanadigani esa hozir
hisoblanardi.

Mavjud yozuvlar uchun ustun NULL qoladi (yakunlanish vaqti tarixda saqlanmagan) —
frontend NULL bo'lganlarni haftalik hisobga qo'shmaydi.

Revision ID: c3a91d47f052
Revises: f8413462b774
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3a91d47f052"
down_revision: Union[str, Sequence[str], None] = "f8413462b774"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}

    if "completed_at" not in columns:
        op.add_column(
            "orders",
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "completed_at")
