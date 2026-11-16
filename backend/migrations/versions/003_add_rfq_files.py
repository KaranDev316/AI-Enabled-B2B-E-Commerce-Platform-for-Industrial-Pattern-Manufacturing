"""Add rfq_files table for Slice S06

Revision ID: 003
Revises: 002
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rfq_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rfq_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rfq_files_rfq_id'), 'rfq_files', ['rfq_id'], unique=False)
    op.create_index(op.f('ix_rfq_files_storage_key'), 'rfq_files', ['storage_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_rfq_files_storage_key'), table_name='rfq_files')
    op.drop_index(op.f('ix_rfq_files_rfq_id'), table_name='rfq_files')
    op.drop_table('rfq_files')
