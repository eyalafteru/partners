"""Add Facebook Marketing tables

Revision ID: 003_add_facebook_marketing
Revises: 002_add_pipeline_stage
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '003_add_facebook_marketing'
down_revision = '002_pipeline_stage'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Facebook Groups
    op.create_table(
        'facebook_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fb_group_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('member_count', sa.Integer(), default=0),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('group_image_url', sa.String(500), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('auto_reply_enabled', sa.Boolean(), default=True),
        sa.Column('posting_delay_minutes', sa.Integer(), default=30),
        sa.Column('total_posts', sa.Integer(), default=0),
        sa.Column('total_replies_received', sa.Integer(), default=0),
        sa.Column('total_conversations', sa.Integer(), default=0),
        sa.Column('last_post_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fb_group_id')
    )
    op.create_index('ix_facebook_groups_fb_group_id', 'facebook_groups', ['fb_group_id'])
    op.create_index('ix_facebook_groups_id', 'facebook_groups', ['id'])

    # Facebook Post Templates
    op.create_table(
        'facebook_post_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_content', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('include_image', sa.Boolean(), default=True),
        sa.Column('image_prompt_template', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('times_used', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_facebook_post_templates_id', 'facebook_post_templates', ['id'])

    # Facebook Campaigns
    op.create_table(
        'facebook_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('topic', sa.String(200), nullable=False),
        sa.Column('target_audience', sa.String(200), nullable=True),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('facebook_post_templates.id'), nullable=True),
        sa.Column('image_percentage', sa.Integer(), default=50),
        sa.Column('delay_between_posts', sa.Integer(), default=60),
        sa.Column('max_posts_per_day', sa.Integer(), default=10),
        sa.Column('target_group_ids', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('total_posts_generated', sa.Integer(), default=0),
        sa.Column('total_posts_approved', sa.Integer(), default=0),
        sa.Column('total_posts_published', sa.Integer(), default=0),
        sa.Column('total_replies', sa.Integer(), default=0),
        sa.Column('total_conversations', sa.Integer(), default=0),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_facebook_campaigns_id', 'facebook_campaigns', ['id'])

    # Facebook Posts
    op.create_table(
        'facebook_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('facebook_campaigns.id'), nullable=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('facebook_groups.id'), nullable=False),
        sa.Column('fb_post_id', sa.String(100), nullable=True),
        sa.Column('fb_post_url', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('has_image', sa.Boolean(), default=False),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('apify_run_id', sa.String(100), nullable=True),
        sa.Column('publish_error', sa.Text(), nullable=True),
        sa.Column('replies_count', sa.Integer(), default=0),
        sa.Column('messenger_conversations', sa.Integer(), default=0),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fb_post_id')
    )
    op.create_index('ix_facebook_posts_id', 'facebook_posts', ['id'])
    op.create_index('ix_facebook_posts_fb_post_id', 'facebook_posts', ['fb_post_id'])

    # Facebook Replies
    op.create_table(
        'facebook_replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('facebook_posts.id'), nullable=False),
        sa.Column('fb_comment_id', sa.String(100), nullable=True),
        sa.Column('fb_user_id', sa.String(100), nullable=True),
        sa.Column('fb_user_name', sa.String(255), nullable=True),
        sa.Column('fb_user_profile_url', sa.String(500), nullable=True),
        sa.Column('fb_user_profile_pic', sa.String(500), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('ai_detected_intent', sa.String(50), nullable=True),
        sa.Column('ai_intent_confidence', sa.Float(), nullable=True),
        sa.Column('wants_private', sa.Boolean(), default=False),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), default='new'),
        sa.Column('suggested_response', sa.Text(), nullable=True),
        sa.Column('suggested_channel', sa.String(20), nullable=True),
        sa.Column('actual_response', sa.Text(), nullable=True),
        sa.Column('response_channel', sa.String(20), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fb_comment_id')
    )
    op.create_index('ix_facebook_replies_id', 'facebook_replies', ['id'])
    op.create_index('ix_facebook_replies_fb_comment_id', 'facebook_replies', ['fb_comment_id'])
    op.create_index('ix_facebook_replies_fb_user_id', 'facebook_replies', ['fb_user_id'])

    # Facebook Conversations
    op.create_table(
        'facebook_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('initial_reply_id', sa.Integer(), sa.ForeignKey('facebook_replies.id'), nullable=True),
        sa.Column('fb_user_id', sa.String(100), nullable=False),
        sa.Column('fb_user_name', sa.String(255), nullable=True),
        sa.Column('fb_user_profile_url', sa.String(500), nullable=True),
        sa.Column('current_channel', sa.String(20), default='comment'),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('ai_context', sa.JSON(), nullable=True),
        sa.Column('converted_to_lead', sa.Boolean(), default=False),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('messages_count', sa.Integer(), default=0),
        sa.Column('ai_responses_count', sa.Integer(), default=0),
        sa.Column('human_responses_count', sa.Integer(), default=0),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_facebook_conversations_id', 'facebook_conversations', ['id'])
    op.create_index('ix_facebook_conversations_fb_user_id', 'facebook_conversations', ['fb_user_id'])

    # Facebook Messages
    op.create_table(
        'facebook_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('facebook_conversations.id'), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(10), nullable=True),
        sa.Column('is_approved', sa.Boolean(), default=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_sent', sa.Boolean(), default=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('send_error', sa.Text(), nullable=True),
        sa.Column('fb_message_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_facebook_messages_id', 'facebook_messages', ['id'])


def downgrade() -> None:
    op.drop_table('facebook_messages')
    op.drop_table('facebook_conversations')
    op.drop_table('facebook_replies')
    op.drop_table('facebook_posts')
    op.drop_table('facebook_campaigns')
    op.drop_table('facebook_post_templates')
    op.drop_table('facebook_groups')
