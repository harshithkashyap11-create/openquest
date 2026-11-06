"""Add class-scoped inclusive lesson sources.

Revision ID: 0009_inclusive_sources
Revises: 0008_classroom_studio
"""
from alembic import op
import sqlalchemy as sa

revision = '0009_inclusive_sources'
down_revision = '0008_classroom_studio'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('inclusive_sources',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('class_id', sa.Uuid(), sa.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('teachers.id'), nullable=False),
        sa.Column('source', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_inclusive_sources_class_id', 'inclusive_sources', ['class_id'])


def downgrade():
    op.drop_index('ix_inclusive_sources_class_id', table_name='inclusive_sources')
    op.drop_table('inclusive_sources')
