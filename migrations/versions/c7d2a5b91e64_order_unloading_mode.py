"""Buyurtmaga tushirish sharti: unloading_mode, unloading_wait_hours

Mijoz yuk manzilga yetib borgandan keyingi shartni tanlay oladi: o'sha zahoti
tushirib olish, bir necha soat kutish yoki kun kutish. Haydovchi uchun bu reysdan
keyin mashina qancha band bo'lishini bildiradi.

Ikkala ustun ham NULL bo'lishi mumkin: tanlov ixtiyoriy, mavjud buyurtmalarda esa
umuman bo'lmagan.

`create_all` bu ustunlarni MAVJUD `orders` jadvaliga qo'sha olmaydi (u faqat yetishmayotgan
jadvalni yaratadi), shuning uchun migratsiya shart.

Revision ID: c7d2a5b91e64
Revises: 0ea3c62b3a70
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d2a5b91e64"
down_revision: Union[str, Sequence[str], None] = "0ea3c62b3a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UNLOADING_MODE = sa.Enum(
    "IMMEDIATE", "HOURS", "DAY", name="unloadingmode", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Enum tipini ustundan ALOHIDA yaratamiz: `create_all` ilgari ishlab bo'lgan
    # bazada tip allaqachon mavjud bo'lishi mumkin, `add_column` esa uni qayta
    # yaratishga urinib "type already exists" bilan yiqilardi.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE unloadingmode AS ENUM ('IMMEDIATE', 'HOURS', 'DAY'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    order_columns = {col["name"] for col in inspector.get_columns("orders")}
    if "unloading_mode" not in order_columns:
        op.add_column("orders", sa.Column("unloading_mode", UNLOADING_MODE, nullable=True))
    if "unloading_wait_hours" not in order_columns:
        op.add_column(
            "orders", sa.Column("unloading_wait_hours", sa.SmallInteger(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "unloading_wait_hours")
    op.drop_column("orders", "unloading_mode")
    op.execute("DROP TYPE IF EXISTS unloadingmode")
