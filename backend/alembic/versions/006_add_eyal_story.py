"""Add eyal_story table for personal story management

Revision ID: 006
Revises: 005
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create eyal_story table - single row table for Eyal's personal story
    op.create_table(
        'eyal_story',
        sa.Column('id', sa.Integer(), nullable=False, default=1, comment='Always 1 - single row'),
        sa.Column('story_content', sa.Text(), nullable=False, comment='Full story content - free text'),
        sa.Column('forbidden_phrases', sa.Text(), nullable=True, comment='Phrases AI should not use - one per line'),
        sa.Column('ai_instructions', sa.Text(), nullable=True, comment='Additional AI instructions'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_eyal_story_id', 'eyal_story', ['id'])


def downgrade():
    op.drop_index('ix_eyal_story_id', 'eyal_story')
    op.drop_table('eyal_story')
