"""Qidiruvni qo'lda to'xtatish: orders.dispatch_paused_at

Sender haydovchi qidiruvini vaqtincha to'xtata oladi. To'xtatilgan buyurtmaga yangi
raund yuborilmaydi (`services/dispatch.py` `_dispatch_next` va sweeper'lar shu ustunni
tekshiradi) va aynan shu paytda narxni o'zgartirish mumkin bo'ladi.

NULL — qidiruv to'xtatilmagan (mavjud buyurtmalarning hammasi shunday).

`create_all` mavjud `orders` jadvaliga ustun qo'sha olmaydi, shuning uchun migratsiya shart.

Revision ID: d8e3b6c04f27
Revises: c7d2a5b91e64
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8e3b6c04f27"
down_revision: Union[str, Sequence[str], None] = "c7d2a5b91e64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    order_columns = {col["name"] for col in inspector.get_columns("orders")}
    if "dispatch_paused_at" not in order_columns:
        op.add_column(
            "orders",
            sa.Column("dispatch_paused_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "dispatch_paused_at")
