"""S13 manual materials and immutable stock adjustment history."""
from alembic import op
import sqlalchemy as sa
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('inventory_materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(40), unique=True, nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Numeric(14,3), server_default='0', nullable=False),
        sa.Column('minimum_stock', sa.Numeric(14,3), server_default='0', nullable=False),
        sa.Column('location', sa.String(150)), sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('quantity >= 0 AND quantity <= 99999999999.999', name='ck_inventory_quantity'),
        sa.CheckConstraint('minimum_stock >= 0 AND minimum_stock <= 99999999999.999', name='ck_inventory_minimum'))
    op.create_table('stock_adjustments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('request_id', sa.String(36), unique=True, nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('inventory_materials.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('material_code', sa.String(40), nullable=False), sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False), sa.Column('amount', sa.Numeric(14,3), nullable=False),
        sa.Column('quantity_before', sa.Numeric(14,3), nullable=False), sa.Column('quantity_after', sa.Numeric(14,3), nullable=False),
        sa.Column('reason', sa.String(1000), nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_stock_adjustment_positive'),
        sa.CheckConstraint('quantity_before >= 0 AND quantity_after >= 0', name='ck_stock_adjustment_balances'),
        sa.CheckConstraint("direction IN ('addition', 'deduction')", name='ck_stock_adjustment_direction'))
    op.create_index('ix_stock_adjustments_material_id', 'stock_adjustments', ['material_id'])


def downgrade():
    op.drop_index('ix_stock_adjustments_material_id', table_name='stock_adjustments')
    op.drop_table('stock_adjustments')
    op.drop_table('inventory_materials')
