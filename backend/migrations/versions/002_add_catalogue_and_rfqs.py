"""Add categories, products, and rfqs tables

Revision ID: 002
Revises: 001
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. categories table
    categories_table = op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # 2. products table
    products_table = op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('material_type', sa.String(length=100), nullable=True),
        sa.Column('indicative_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_products_slug'), 'products', ['slug'], unique=True)

    # 3. rfqs table
    op.create_table(
        'rfqs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rfq_number', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('rfq_type', sa.String(length=50), server_default='custom', nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('material', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dimensions', sa.String(length=255), nullable=True),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('target_delivery_date', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='submitted', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rfqs_customer_id'), 'rfqs', ['customer_id'], unique=False)
    op.create_index(op.f('ix_rfqs_rfq_number'), 'rfqs', ['rfq_number'], unique=True)

    # 4. Seed 3 standard KPC industrial pattern products
    op.bulk_insert(
        categories_table,
        [
            {'id': 1, 'name': 'Foundry Patterns', 'description': 'Wooden & Metallic foundry casting patterns'},
            {'id': 2, 'name': 'Industrial Dies', 'description': 'Precision CNC press tools and die patterns'},
        ],
    )
    op.bulk_insert(
        products_table,
        [
            {
                'id': 1,
                'category_id': 1,
                'name': 'Heavy Duty Wooden Foundry Pattern',
                'slug': 'heavy-duty-wooden-foundry-pattern',
                'description': 'Seasoned Teak/Mahogany wood pattern with protective polyurethane coating for sand casting.',
                'material_type': 'Teak Wood',
                'indicative_price': 18500.00,
                'is_active': True,
            },
            {
                'id': 2,
                'category_id': 2,
                'name': 'CNC Precision Metallic Die Pattern',
                'slug': 'cnc-precision-metallic-die-pattern',
                'description': 'High-tensile Aluminum Alloy 7075 metallic die pattern machined to ±0.05mm tolerance.',
                'material_type': 'Aluminum Alloy 7075',
                'indicative_price': 42000.00,
                'is_active': True,
            },
            {
                'id': 3,
                'category_id': 1,
                'name': 'Engine Block Core Box Pattern',
                'slug': 'engine-block-core-box-pattern',
                'description': 'Multi-piece Cast Iron core box pattern with hardened steel guide pins for automotive engines.',
                'material_type': 'Cast Iron Grade 25',
                'indicative_price': 78000.00,
                'is_active': True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_rfqs_rfq_number'), table_name='rfqs')
    op.drop_index(op.f('ix_rfqs_customer_id'), table_name='rfqs')
    op.drop_table('rfqs')
    op.drop_index(op.f('ix_products_slug'), table_name='products')
    op.drop_table('products')
    op.drop_table('categories')
