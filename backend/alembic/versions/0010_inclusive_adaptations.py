"""Add inclusive drafts and student assignments."""
from alembic import op
import sqlalchemy as sa
revision = '0010_inclusive_adaptations'
down_revision = '0009_inclusive_sources'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('inclusive_adaptations',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('class_id', sa.Uuid(), sa.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_id', sa.Uuid(), sa.ForeignKey('inclusive_sources.id'), nullable=False),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('teachers.id'), nullable=False),
        sa.Column('supports', sa.JSON(), nullable=False), sa.Column('analysis', sa.JSON(), nullable=False),
        sa.Column('draft', sa.JSON(), nullable=False), sa.Column('findings', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False), sa.Column('approved_version', sa.Integer()),
        sa.Column('review_note', sa.Text()), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_inclusive_adaptations_class_id', 'inclusive_adaptations', ['class_id'])
    op.create_table('inclusive_assignments',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('adaptation_id', sa.Uuid(), sa.ForeignKey('inclusive_adaptations.id'), nullable=False),
        sa.Column('student_id', sa.Uuid(), sa.ForeignKey('students.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False), sa.Column('content', sa.JSON(), nullable=False), sa.Column('progress', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('adaptation_id', 'student_id', 'version', name='uq_inclusive_assignment'))
    op.create_index('ix_inclusive_assignments_student_id', 'inclusive_assignments', ['student_id'])
    op.create_table('inclusive_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('adaptation_id', sa.Uuid(), sa.ForeignKey('inclusive_adaptations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('teachers.id'), nullable=False),
        sa.Column('action', sa.Text(), nullable=False), sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_inclusive_history_adaptation_id', 'inclusive_history', ['adaptation_id'])


def downgrade():
    op.drop_index('ix_inclusive_history_adaptation_id', table_name='inclusive_history')
    op.drop_table('inclusive_history')
    op.drop_index('ix_inclusive_assignments_student_id', table_name='inclusive_assignments')
    op.drop_table('inclusive_assignments')
    op.drop_index('ix_inclusive_adaptations_class_id', table_name='inclusive_adaptations')
    op.drop_table('inclusive_adaptations')
