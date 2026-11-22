"""S12 private production issues and handling history."""
from alembic import op
import sqlalchemy as sa
revision='011'
down_revision='010'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('production_issues',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('employee_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('job_id',sa.Integer(),sa.ForeignKey('production_jobs.id',ondelete='RESTRICT'),nullable=True),
        sa.Column('issue_type',sa.String(30),nullable=False),sa.Column('title',sa.String(200),nullable=False),
        sa.Column('description',sa.Text(),nullable=False),sa.Column('priority',sa.String(10),nullable=False),
        sa.Column('status',sa.String(20),server_default='open',nullable=False),
        sa.Column('version',sa.Integer(),server_default='0',nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("issue_type IN ('production','machine','material','drawing')",name='ck_issue_type'),
        sa.CheckConstraint("priority IN ('high','medium','low')",name='ck_issue_priority'),
        sa.CheckConstraint("status IN ('open','in_review','in_progress','resolved')",name='ck_issue_status'))
    op.create_index('ix_production_issues_employee_id','production_issues',['employee_id'])
    op.create_table('production_issue_files',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('issue_id',sa.Integer(),sa.ForeignKey('production_issues.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('storage_key',sa.String(255),unique=True,nullable=False),
        sa.Column('file_name',sa.String(255),nullable=False),sa.Column('content_type',sa.String(50),nullable=False),
        sa.Column('file_size_bytes',sa.Integer(),nullable=False))
    op.create_index('ix_production_issue_files_issue_id','production_issue_files',['issue_id'])
    op.create_table('production_issue_events',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('issue_id',sa.Integer(),sa.ForeignKey('production_issues.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),sa.Column('note',sa.String(2000),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_production_issue_events_issue_id','production_issue_events',['issue_id'])

def downgrade():
    for table in ('production_issue_events','production_issue_files','production_issues'):
        op.drop_table(table)
