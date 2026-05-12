"""add reply_type and banner_type to lead_posts

Revision ID: 015
Revises: 014
Create Date: 2026-05-12

reply_type: text / banner
banner_type: savings / trust (only when reply_type=banner)
"""
from alembic import op
import sqlalchemy as sa


revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lead_posts', sa.Column('reply_type', sa.String(20), nullable=True))
    op.add_column('lead_posts', sa.Column('banner_type', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_posts', 'banner_type')
    op.drop_column('lead_posts', 'reply_type')
