"""S10 one job/employee per order and append-only progress history."""
import sqlalchemy as sa
from alembic import op
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('production_jobs',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('order_id',sa.Integer(),sa.ForeignKey('orders.id',ondelete='RESTRICT'),unique=True,nullable=False),
        sa.Column('employee_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('instructions',sa.Text(),nullable=False),
        sa.Column('stage',sa.String(40),server_default='design_and_tooling',nullable=False),
        sa.Column('progress',sa.Integer(),server_default='0',nullable=False),
        sa.Column('is_paused',sa.Boolean(),server_default=sa.false(),nullable=False),
        sa.Column('version',sa.Integer(),server_default='0',nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint('progress >= 0 AND progress <= 100',name='ck_job_progress'))
    op.create_index('ix_production_jobs_employee_id','production_jobs',['employee_id'])
    op.create_table('job_stage_history',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('job_id',sa.Integer(),sa.ForeignKey('production_jobs.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('from_stage',sa.String(40)),sa.Column('to_stage',sa.String(40),nullable=False),
        sa.Column('action',sa.String(30),nullable=False),sa.Column('progress',sa.Integer(),nullable=False),
        sa.Column('is_paused',sa.Boolean(),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('note',sa.Text(),nullable=False),sa.Column('customer_note',sa.String(500)),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_job_stage_history_job_id','job_stage_history',['job_id'])

def downgrade():
    op.drop_index('ix_job_stage_history_job_id',table_name='job_stage_history')
    op.drop_table('job_stage_history')
    op.drop_index('ix_production_jobs_employee_id',table_name='production_jobs')
    op.drop_table('production_jobs')
