"""Initial schema - all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-21

PartnerCalc OS - יצירת כל הטבלאות הראשוניות
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== טבלת מחשבונים =====
    op.create_table('calculators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='שם המחשבון'),
        sa.Column('target_url', sa.String(length=500), nullable=False, comment='קישור לעמוד המחשבון'),
        sa.Column('intent_description', sa.Text(), nullable=True, comment='תיאור מפורט - למי זה מתאים?'),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True, comment='מילות מפתח לחיפוש וסיווג'),
        sa.Column('embed_code_template', sa.Text(), nullable=True, comment='קוד HTML/JS להטמעה'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True, comment='האם המחשבון פעיל?'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calculators_id'), 'calculators', ['id'], unique=False)

    # ===== טבלת קמפיינים/סריקות =====
    op.create_table('scan_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='שם הסריקה'),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True, comment='מילות מפתח לחיפוש'),
        sa.Column('category', sa.String(length=100), nullable=True, comment='קטגוריה'),
        sa.Column('results_per_query', sa.Integer(), nullable=True, default=100, comment='כמות תוצאות לכל שאילתה'),
        sa.Column('total_urls', sa.Integer(), nullable=True, default=0, comment='כמה URLs נאספו'),
        sa.Column('scanned_count', sa.Integer(), nullable=True, default=0, comment='כמה נסרקו'),
        sa.Column('matched_count', sa.Integer(), nullable=True, default=0, comment='כמה נמצאה התאמה'),
        sa.Column('discarded_count', sa.Integer(), nullable=True, default=0, comment='כמה נפסלו'),
        sa.Column('contacted_count', sa.Integer(), nullable=True, default=0, comment='כמה נשלחה להם פנייה'),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('apify_run_id', sa.String(length=100), nullable=True, comment='ID של הריצה ב-Apify'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_campaigns_id'), 'scan_campaigns', ['id'], unique=False)
    op.create_index(op.f('ix_scan_campaigns_status'), 'scan_campaigns', ['status'], unique=False)

    # ===== טבלת לידים =====
    op.create_table('leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False, comment='דומיין האתר'),
        sa.Column('site_name', sa.String(length=255), nullable=True, comment='שם האתר/העסק'),
        sa.Column('category', sa.String(length=100), nullable=True, comment='קטגוריה'),
        sa.Column('contact_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='{email, phone, whatsapp, name}'),
        sa.Column('seo_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='{dr, monthly_traffic, backlinks}'),
        sa.Column('ai_status', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='{is_real, relevance_score, reasoning}'),
        sa.Column('status', sa.String(length=50), nullable=True, default='new'),
        sa.Column('recommended_calc_id', sa.Integer(), nullable=True),
        sa.Column('source_campaign_id', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True, comment='ה-URL המקורי מגוגל'),
        sa.Column('google_position', sa.Integer(), nullable=True, comment='מיקום בתוצאות גוגל'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_contacted_at', sa.DateTime(timezone=True), nullable=True, comment='תאריך פנייה אחרונה'),
        sa.ForeignKeyConstraint(['recommended_calc_id'], ['calculators.id'], ),
        sa.ForeignKeyConstraint(['source_campaign_id'], ['scan_campaigns.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain')
    )
    op.create_index(op.f('ix_leads_domain'), 'leads', ['domain'], unique=True)
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)

    # ===== טבלת תקשורת =====
    op.create_table('communication',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False, comment='whatsapp, email, sms'),
        sa.Column('direction', sa.String(length=10), nullable=False, comment='inbound, outbound'),
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True, comment='נושא - רלוונטי למייל בלבד'),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending', comment='pending, sent, delivered, read, replied, failed'),
        sa.Column('external_id', sa.String(length=100), nullable=True, comment='ID מהשירות החיצוני'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='הודעת שגיאה אם נכשל'),
        sa.Column('is_auto_reply', sa.Boolean(), nullable=True, default=False, comment='האם זו תשובה אוטומטית של AI'),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_communication_id'), 'communication', ['id'], unique=False)
    op.create_index(op.f('ix_communication_lead_id'), 'communication', ['lead_id'], unique=False)

    # ===== טבלת התקנות =====
    op.create_table('installations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('calc_id', sa.Integer(), nullable=False),
        sa.Column('embed_page_url', sa.String(length=500), nullable=False, comment='העמוד שבו הוטמע המחשבון'),
        sa.Column('is_link_live', sa.Boolean(), nullable=True, default=True, comment='האם הקישור עדיין קיים?'),
        sa.Column('violation_count', sa.Integer(), nullable=True, default=0, comment='כמה פעמים הוסר הקישור'),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True, comment='בדיקה אחרונה'),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True, comment='תאריך הסרה'),
        sa.ForeignKeyConstraint(['calc_id'], ['calculators.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_installations_id'), 'installations', ['id'], unique=False)

    # ===== טבלת תור סריקות =====
    op.create_table('scan_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True, comment='כותרת מגוגל'),
        sa.Column('description', sa.Text(), nullable=True, comment='תיאור מגוגל'),
        sa.Column('google_position', sa.Integer(), nullable=True, comment='מיקום בתוצאות'),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='הודעת שגיאה אם נכשל'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['scan_campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_queue_id'), 'scan_queue', ['id'], unique=False)
    op.create_index(op.f('ix_scan_queue_campaign_id'), 'scan_queue', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_scan_queue_status'), 'scan_queue', ['status'], unique=False)

    # ===== טבלת פרומפטים =====
    op.create_table('prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=50), nullable=False, comment='שם טכני'),
        sa.Column('display_name', sa.String(length=100), nullable=True, comment='שם תצוגה בעברית'),
        sa.Column('description', sa.Text(), nullable=True, comment='הסבר על הצומת'),
        sa.Column('system_prompt', sa.Text(), nullable=True, comment='System prompt'),
        sa.Column('user_prompt_template', sa.Text(), nullable=True, comment='User prompt עם placeholders'),
        sa.Column('available_variables', postgresql.ARRAY(sa.String()), nullable=True, comment='משתנים זמינים'),
        sa.Column('model_name', sa.String(length=50), nullable=True, default='dictalm-atomic-v2-q4'),
        sa.Column('temperature', sa.Float(), nullable=True, default=0.7),
        sa.Column('max_tokens', sa.Integer(), nullable=True, default=500),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('node_name')
    )
    op.create_index(op.f('ix_prompts_id'), 'prompts', ['id'], unique=False)

    # ===== טבלת לוגים AI =====
    op.create_table('ai_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='הנתונים שהוזנו'),
        sa.Column('full_prompt', sa.Text(), nullable=True, comment='הפרומפט המלא'),
        sa.Column('response', sa.Text(), nullable=True, comment='תשובת ה-AI'),
        sa.Column('response_parsed', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='התשובה מפורסרת'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True, comment='זמן ריצה במילישניות'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, comment='כמות טוקנים'),
        sa.Column('success', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_logs_id'), 'ai_logs', ['id'], unique=False)
    op.create_index(op.f('ix_ai_logs_prompt_id'), 'ai_logs', ['prompt_id'], unique=False)
    op.create_index(op.f('ix_ai_logs_lead_id'), 'ai_logs', ['lead_id'], unique=False)

    # ===== טבלת API Keys =====
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False, comment='whatsapp, sendgrid, twilio...'),
        sa.Column('display_name', sa.String(length=100), nullable=True, comment='שם תצוגה'),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='Credentials מוצפנים'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True, comment='בדיקת חיבור אחרונה'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='שגיאה אחרונה'),
        sa.Column('usage_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='סטטיסטיקות שימוש'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_name')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)

    # ===== טבלת הגדרות Auto-Reply =====
    op.create_table('auto_reply_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=True, default='suggest', comment='off, suggest, auto'),
        sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}, comment='כללים'),
        sa.Column('delay_seconds', sa.Integer(), nullable=True, default=30, comment='זמן המתנה לפני תשובה'),
        sa.Column('max_auto_replies', sa.Integer(), nullable=True, default=3, comment='מקסימום תשובות אוטומטיות'),
        sa.Column('fallback_message', sa.Text(), nullable=True, comment='הודעת fallback'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auto_reply_settings_id'), 'auto_reply_settings', ['id'], unique=False)

    # ===== טבלת תשובות ממתינות =====
    op.create_table('pending_replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('communication_id', sa.Integer(), nullable=False),
        sa.Column('suggested_reply', sa.Text(), nullable=False),
        sa.Column('ai_reasoning', sa.Text(), nullable=True, comment='למה ה-AI הציע את זה'),
        sa.Column('status', sa.String(length=20), nullable=True, default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['communication_id'], ['communication.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_replies_id'), 'pending_replies', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('pending_replies')
    op.drop_table('auto_reply_settings')
    op.drop_table('api_keys')
    op.drop_table('ai_logs')
    op.drop_table('prompts')
    op.drop_table('scan_queue')
    op.drop_table('installations')
    op.drop_table('communication')
    op.drop_table('leads')
    op.drop_table('scan_campaigns')
    op.drop_table('calculators')
