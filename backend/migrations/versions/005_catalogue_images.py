"""S04 product specifications and private catalogue image metadata."""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('specifications', sa.Text(), nullable=True))
    op.create_table('product_images',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(255), unique=True, nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False))
    op.create_index('ix_product_images_product_id', 'product_images', ['product_id'])


def downgrade():
    op.drop_index('ix_product_images_product_id', table_name='product_images')
    op.drop_table('product_images')
    op.drop_column('products', 'specifications')
