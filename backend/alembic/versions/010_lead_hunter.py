"""lead_hunter - טבלאות Lead Hunter AI

Revision ID: 010
Revises: 009
Create Date: 2026-02-24

מערכת Lead Hunter AI - קליטת פוסטים מפייסבוק, סיווג AI, התראות WhatsApp
טבלאות: lead_categories, lead_actors, lead_posts, ai_feedback
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '010'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== lead_categories ==========
    op.create_table(
        'lead_categories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('classification_prompt', sa.Text(), nullable=False),
        sa.Column('reply_prompt', sa.Text(), nullable=True),
        sa.Column('whatsapp_phone', sa.String(20), nullable=True),
        sa.Column('whatsapp_name', sa.String(100), nullable=True),
        sa.Column('is_alert_worthy', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('auto_reply_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ========== lead_actors ==========
    op.create_table(
        'lead_actors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('actor_url', sa.String(500), nullable=False, unique=True),
        sa.Column('actor_name', sa.String(255), nullable=False),
        sa.Column('post_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_lead_actors_actor_url', 'lead_actors', ['actor_url'])

    # ========== lead_posts ==========
    op.create_table(
        'lead_posts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('post_url', sa.String(1000), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('group_name', sa.String(255), nullable=True),
        sa.Column('group_url', sa.String(500), nullable=True),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('lead_actors.id'), nullable=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('lead_categories.id'), nullable=True),
        sa.Column('ai_reply', sa.Text(), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='new'),
        sa.Column('whatsapp_sent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('whatsapp_sent_at', sa.DateTime(), nullable=True),
        sa.Column('whatsapp_replied', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('whatsapp_replied_at', sa.DateTime(), nullable=True),
        sa.Column('auto_reply_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('auto_reply_sent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('auto_reply_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_lead_posts_post_url', 'lead_posts', ['post_url'])
    op.create_index('ix_lead_posts_status', 'lead_posts', ['status'])
    op.create_index('ix_lead_posts_actor_id', 'lead_posts', ['actor_id'])
    op.create_index('ix_lead_posts_category_id', 'lead_posts', ['category_id'])

    # ========== ai_feedback ==========
    op.create_table(
        'ai_feedback',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('lead_posts.id'), nullable=False),
        sa.Column('original_category_id', sa.Integer(), nullable=True),
        sa.Column('corrected_category_id', sa.Integer(), nullable=True),
        sa.Column('is_irrelevant', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # ========== Seed default categories ==========
    op.execute(text("""
        INSERT INTO lead_categories (name, description, classification_prompt, reply_prompt, is_alert_worthy, auto_reply_enabled, is_active)
        VALUES
        (
            'חיפוש הובלה',
            'אדם מחפש שירות הובלה - פריט בודד, דירה, משרד',
            'הפוסט הוא חיפוש של אדם שצריך שירות הובלה (פריט בודד, דירה, ספה, מקרר, משרד וכו). האדם מבקש מוביל/חברת הובלות.',
            'כתוב תגובה קצרה ומזמינה לאדם שמחפש שירות הובלה. הצע לעזור, ציין שאתה מקצועי ואמין, בקש שיצור קשר.',
            1, 0, 1
        ),
        (
            'הלוואה פרטית / מימון נכס',
            'אדם מחפש הלוואה פרטית או מימון כנגד נכס',
            'הפוסט הוא חיפוש של אדם שצריך הלוואה פרטית, מימון, או אשראי כנגד נכס/דירה.',
            'כתוב תגובה קצרה ומקצועית לאדם שמחפש הלוואה פרטית. ציין שאתה יכול לעזור ולבדוק אפשרויות.',
            1, 0, 1
        ),
        (
            'הלוואה עסקית',
            'עסק מחפש הלוואה עסקית או מימון לעסק',
            'הפוסט הוא חיפוש של עסק שצריך הלוואה עסקית, קו אשראי, או מימון לפעילות עסקית.',
            'כתוב תגובה קצרה ומקצועית לעסק שמחפש מימון. ציין שיש פתרונות מותאמים לעסקים.',
            1, 0, 1
        ),
        (
            'פרסום מתחרה',
            'חברת הובלות או מוביל שמפרסם שירותים שלו',
            'הפוסט הוא פרסום של חברת הובלות או מוביל שמציע את השירות שלו (לא מחפש - מוכר).',
            NULL,
            0, 0, 1
        ),
        (
            'חיפוש נכס מסחרי',
            'אדם או עסק מחפש נכס מסחרי, משרד, מחסן',
            'הפוסט הוא חיפוש של נכס מסחרי - משרד, חנות, מחסן, שטח מסחרי - בדרך כלל במרכז הארץ.',
            'כתוב תגובה קצרה לאדם שמחפש נכס מסחרי. ציין שאתה יכול לעזור ברישום.',
            1, 0, 1
        )
    """))


def downgrade() -> None:
    op.drop_table('ai_feedback')
    op.drop_index('ix_lead_posts_category_id', 'lead_posts')
    op.drop_index('ix_lead_posts_actor_id', 'lead_posts')
    op.drop_index('ix_lead_posts_status', 'lead_posts')
    op.drop_index('ix_lead_posts_post_url', 'lead_posts')
    op.drop_table('lead_posts')
    op.drop_index('ix_lead_actors_actor_url', 'lead_actors')
    op.drop_table('lead_actors')
    op.drop_table('lead_categories')
