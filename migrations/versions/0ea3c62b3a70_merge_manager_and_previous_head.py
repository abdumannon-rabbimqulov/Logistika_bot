"""merge manager and previous head

Revision ID: 0ea3c62b3a70
Revises: b2f7c1a94d03, e9d3f0c85a21
Create Date: 2026-08-05 11:25:05.992102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ea3c62b3a70'
down_revision: Union[str, Sequence[str], None] = ('b2f7c1a94d03', 'e9d3f0c85a21')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
