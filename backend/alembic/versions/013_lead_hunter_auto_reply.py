"""lead_hunter_auto_reply - תגובה אוטומטית דרך תוסף Chrome

Revision ID: 013
Revises: 012
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa


revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lead_posts', sa.Column('auto_reply_status', sa.String(20), nullable=True))
    op.add_column('lead_categories', sa.Column('auto_reply_daily_limit', sa.Integer(), server_default='10'))
    op.add_column('lead_categories', sa.Column('auto_reply_delay_minutes', sa.Integer(), server_default='10'))


def downgrade() -> None:
    op.drop_column('lead_posts', 'auto_reply_status')
    op.drop_column('lead_categories', 'auto_reply_daily_limit')
    op.drop_column('lead_categories', 'auto_reply_delay_minutes')
