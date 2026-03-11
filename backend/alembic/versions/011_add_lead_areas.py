"""add_lead_areas - טבלת אזורים גיאוגרפיים + עמודת area בפוסטים

Revision ID: 011
Revises: 010
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== lead_areas ==========
    op.create_table(
        'lead_areas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('is_reply_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_whatsapp_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # ========== Seed default areas ==========
    op.execute(text("""
        INSERT INTO lead_areas (name, is_reply_enabled, is_whatsapp_enabled, is_visible)
        VALUES
        ('מרכז', 1, 1, 1),
        ('שרון', 1, 1, 1),
        ('שפלה', 1, 1, 1),
        ('ירושלים', 1, 1, 1),
        ('צפון', 1, 1, 1),
        ('דרום', 1, 1, 1),
        ('לא ידוע', 1, 1, 1)
    """))

    # ========== area column on lead_posts ==========
    op.add_column('lead_posts', sa.Column('area', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_posts', 'area')
    op.drop_table('lead_areas')
