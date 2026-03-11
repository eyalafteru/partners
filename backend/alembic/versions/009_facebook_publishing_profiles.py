"""facebook_publishing_profiles - פרופילים לפרסום (מעבר בין יוזרים)

Revision ID: 009
Revises: 008
Create Date: 2026-02-18

מאפשר מספר פרופילי פרסום (למשל אייל / שלי). רק פרופיל אחד פעיל בכל זמן.
קריאת Cookie לפרסום: קודם מהפרופיל הפעיל, אחרת fallback ל-facebook_cookie_storage ו-.env.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'facebook_publishing_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cookie_json', sa.Text(), nullable=True),
        sa.Column('cookie_hash', sa.String(64), nullable=True),
        sa.Column('source_machine', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    # Seed: copy from legacy facebook_cookie_storage id=1 if exists
    conn = op.get_bind()
    try:
        r = conn.execute(text("SELECT cookie_json, cookie_hash, source_machine FROM facebook_cookie_storage WHERE id = 1")).fetchone()
    except Exception:
        r = None
    if r and r[0]:
        conn.execute(text("""
            INSERT INTO facebook_publishing_profiles (name, cookie_json, cookie_hash, source_machine, is_active, updated_at, created_at)
            VALUES (:name, :cj, :ch, :sm, 1, NOW(), NOW())
        """), {"name": "פרופיל 1", "cj": r[0], "ch": (r[1] or "") if len(r) > 1 else "", "sm": (r[2] or "") if len(r) > 2 else ""})
    else:
        conn.execute(text("""
            INSERT INTO facebook_publishing_profiles (name, is_active, updated_at, created_at)
            VALUES ('פרופיל 1', 1, NOW(), NOW())
        """))


def downgrade() -> None:
    op.drop_table('facebook_publishing_profiles')
