"""Haydovchi: liniyaga kelajakdagi sanadan chiqish (available_from_date)

Revision ID: bb726de280e6
Revises: 8b1137822e41
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bb726de280e6"
down_revision: Union[str, Sequence[str], None] = "8b1137822e41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("drivers")}
    if "available_from_date" not in columns:
        op.add_column("drivers", sa.Column("available_from_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("drivers", "available_from_date")
