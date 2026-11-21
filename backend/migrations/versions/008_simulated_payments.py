"""S09 append-only simulated payment ledger with database idempotency."""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('simulated_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('idempotency_key', sa.String(36), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('outcome', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('idempotency_key', name='uq_simulated_payment_key'),
        sa.CheckConstraint('amount > 0', name='ck_simulated_payment_positive'),
        sa.CheckConstraint("outcome IN ('succeeded', 'failed')", name='ck_simulated_payment_outcome'))
    op.create_index('ix_simulated_payments_invoice_id', 'simulated_payments', ['invoice_id'])


def downgrade():
    op.drop_table('simulated_payments')
