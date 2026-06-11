"""add_status_to_messages

Revision ID: 1179eea8a15e
Revises: d5f9d6ed31d1
Create Date: 2026-06-11 17:59:42.587979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1179eea8a15e'
down_revision: Union[str, Sequence[str], None] = 'd5f9d6ed31d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create Enum type safely
    messagestatus = postgresql.ENUM('SENDING', 'SENT', 'DELIVERED', 'READ', name='messagestatus')
    messagestatus.create(op.get_bind(), checkfirst=True)

    # 2. Add column as nullable=True first
    op.add_column('messages', sa.Column('status', messagestatus, nullable=True))
    op.add_column('messages', sa.Column('reply_to_id', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('messages', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('messages', sa.Column('client_uuid', sa.String(length=36), nullable=True))
    
    op.create_index(op.f('ix_messages_client_uuid'), 'messages', ['client_uuid'], unique=False)
    op.create_foreign_key(None, 'messages', 'messages', ['reply_to_id'], ['id'], ondelete='SET NULL')

    # 3. Populate existing data with default value
    op.execute("UPDATE messages SET status = 'SENT' WHERE status IS NULL")

    # 4. Alter column to nullable=False
    op.alter_column('messages', 'status', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.drop_index(op.f('ix_messages_client_uuid'), table_name='messages')
    op.drop_column('messages', 'client_uuid')
    op.drop_column('messages', 'deleted_at')
    op.drop_column('messages', 'is_deleted')
    op.drop_column('messages', 'reply_to_id')
    op.drop_column('messages', 'status')
    
    # Drop enum type safely
    messagestatus = postgresql.ENUM('SENDING', 'SENT', 'DELIVERED', 'READ', name='messagestatus')
    messagestatus.drop(op.get_bind(), checkfirst=True)
