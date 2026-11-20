"""S08 immutable order/invoice snapshots and cancellation history."""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def commercial_columns():
    return [
        sa.Column('customer_name_snapshot', sa.String(255), nullable=False),
        sa.Column('customer_gstin_snapshot', sa.String(50)),
        sa.Column('customer_address_snapshot', sa.Text()),
        sa.Column('currency', sa.String(10), nullable=False),
        sa.Column('subtotal_amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('tax_rate_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('items_snapshot_json', sa.Text(), nullable=False),
        sa.Column('paid_amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    with op.batch_alter_table('orders') as batch:
        batch.alter_column('total_amount', existing_type=sa.Numeric(12, 2), type_=sa.Numeric(20, 2), existing_nullable=False)
    op.create_table('order_commercial_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quotation_id', sa.Integer(), sa.ForeignKey('quotations.id')),
        sa.Column('quotation_version', sa.Integer()),
        sa.Column('product_summary', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('estimated_lead_time_days', sa.Integer()),
        sa.Column('successful_payment_count', sa.Integer(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('cancellation_reason', sa.String(500)),
        *commercial_columns())
    op.create_index('ix_order_commercial_snapshots_order_id', 'order_commercial_snapshots', ['order_id'], unique=True)
    op.create_index('ix_order_commercial_snapshots_quotation_id', 'order_commercial_snapshots', ['quotation_id'], unique=True)
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('is_demo_invoice', sa.Boolean(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True)),
        *commercial_columns())
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)
    op.create_index('ix_invoices_order_id', 'invoices', ['order_id'], unique=True)
    op.create_index('ix_invoices_customer_id', 'invoices', ['customer_id'])
    op.create_table('order_status_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('from_status', sa.String(50)),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('note', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_order_status_events_order_id', 'order_status_events', ['order_id'])


def downgrade():
    op.drop_table('order_status_events')
    op.drop_table('invoices')
    op.drop_table('order_commercial_snapshots')
    with op.batch_alter_table('orders') as batch:
        batch.alter_column('total_amount', existing_type=sa.Numeric(20, 2), type_=sa.Numeric(12, 2), existing_nullable=False)
