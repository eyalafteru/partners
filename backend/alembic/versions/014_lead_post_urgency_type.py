"""add urgency_type to lead_posts

Revision ID: 014
Revises: 013
Create Date: 2026-03-16

הוספת שדה urgency_type לטבלת lead_posts - מאפשר מעקב אחרי תת-סוג הפוסט:
urgent (דחוף) / exploring (גישוש) / professional (מקצועי) / general (כללי)
"""
from alembic import op
import sqlalchemy as sa


revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lead_posts', sa.Column('urgency_type', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_posts', 'urgency_type')
