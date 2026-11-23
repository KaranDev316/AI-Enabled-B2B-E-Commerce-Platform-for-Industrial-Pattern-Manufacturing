"""S08: issued commercial records must not disappear through cascading deletes.

Replaces ON DELETE CASCADE with RESTRICT for snapshots, invoices and order history,
so deleting an order or customer row fails instead of silently removing history.
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

TARGETS = [
    ('order_commercial_snapshots', 'order_id', 'orders'),
    ('invoices', 'order_id', 'orders'),
    ('invoices', 'customer_id', 'users'),
    ('order_status_events', 'order_id', 'orders'),
]


def _replace(ondelete):
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return  # Supported deployments use PostgreSQL; SQLite tests build from the models.
    inspector = sa.inspect(bind)
    for table, column, referred in TARGETS:
        for fk in inspector.get_foreign_keys(table):
            if fk['constrained_columns'] == [column] and fk['referred_table'] == referred:
                op.drop_constraint(fk['name'], table, type_='foreignkey')
                op.create_foreign_key(fk['name'], table, referred, [column], ['id'], ondelete=ondelete)


def upgrade():
    _replace('RESTRICT')


def downgrade():
    _replace('CASCADE')
