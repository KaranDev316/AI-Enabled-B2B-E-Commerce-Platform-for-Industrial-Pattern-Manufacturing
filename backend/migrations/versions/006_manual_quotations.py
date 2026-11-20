"""S07 manual versioned quotations, item snapshots and customer responses."""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('quotations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rfq_id', sa.Integer(), sa.ForeignKey('rfqs.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('pricing_source', sa.String(20), nullable=False),
        sa.Column('estimation_id', sa.Integer(), nullable=True),
        sa.Column('tax_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(20, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('total', sa.Numeric(20, 2), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('rfq_id', 'version', name='uq_quotation_rfq_version'),
        sa.CheckConstraint("status IN ('draft','sent','accepted','superseded','expired','rejected')", name='ck_quotation_status'),
        sa.CheckConstraint("pricing_source = 'manual' AND estimation_id IS NULL", name='ck_quotation_manual_source'),
        sa.CheckConstraint('version > 0 AND revision > 0', name='ck_quotation_versions'))
    op.create_index('ix_quotations_rfq_id', 'quotations', ['rfq_id'])
    op.create_table('quotation_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('quotation_id', sa.Integer(), sa.ForeignKey('quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(11, 2), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.CheckConstraint('quantity > 0 AND unit_price >= 0', name='ck_quotation_item_values'))
    op.create_index('ix_quotation_items_quotation_id', 'quotation_items', ['quotation_id'])
    op.create_table('quotation_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('quotation_id', sa.Integer(), sa.ForeignKey('quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("action IN ('reject','request_changes')", name='ck_quotation_decision_action'))
    op.create_index('ix_quotation_decisions_quotation_id', 'quotation_decisions', ['quotation_id'])


def downgrade():
    op.drop_table('quotation_decisions')
    op.drop_table('quotation_items')
    op.drop_table('quotations')
