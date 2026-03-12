"""facebook_action_log - לוג פעולות פייסבוק לזיהוי חסימות

Revision ID: 010
Revises: 009
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa


revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'facebook_action_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action_type', sa.String(30), nullable=False, index=True),
        sa.Column('method', sa.String(40), nullable=False),
        sa.Column('profile_name', sa.String(100), index=True),
        sa.Column('profile_id', sa.Integer()),
        sa.Column('target_url', sa.String(500)),
        sa.Column('post_id', sa.Integer()),
        sa.Column('reply_id', sa.Integer()),
        sa.Column('group_name', sa.String(255)),
        sa.Column('apify_run_id', sa.String(50)),
        sa.Column('success', sa.Boolean(), default=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('facebook_action_log')
