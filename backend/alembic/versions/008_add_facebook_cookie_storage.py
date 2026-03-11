"""add facebook_cookie_storage table

Revision ID: 008
Revises: 007
Create Date: 2026-02-16

טבלה לשמירת קוקי פייסבוק ב-DB כדי לשתף בין מחשבים
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'facebook_cookie_storage',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cookie_json', sa.Text(), nullable=False),
        sa.Column('cookie_hash', sa.String(64), nullable=True),
        sa.Column('source_machine', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('facebook_cookie_storage')
