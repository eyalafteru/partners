"""add debug_ai_prompt column

Revision ID: 007
Revises: 006
Create Date: 2026-02-05

הוספת שדה לשמירת הפרומפט שנשלח ל-AI - לצורך דיבאג
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # הוספת עמודת debug_ai_prompt לטבלת facebook_posts
    op.add_column(
        'facebook_posts',
        sa.Column('debug_ai_prompt', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('facebook_posts', 'debug_ai_prompt')
