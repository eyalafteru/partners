"""Add post strategies and auto-responder fields

Revision ID: 004
Revises: 003
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003_add_facebook_marketing'
branch_labels = None
depends_on = None


def upgrade():
    # Create post_strategies table
    op.create_table(
        'post_strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('icon', sa.String(10), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('post_template', sa.Text(), nullable=True),
        sa.Column('example_post', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('times_used', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_post_strategies_id', 'post_strategies', ['id'])
    op.create_index('ix_post_strategies_slug', 'post_strategies', ['slug'])
    
    # Add new columns to facebook_campaigns
    op.add_column('facebook_campaigns', sa.Column('calculator_id', sa.Integer(), nullable=True))
    op.add_column('facebook_campaigns', sa.Column('calculator_mode', sa.String(20), default='all'))
    op.add_column('facebook_campaigns', sa.Column('calculator_category', sa.String(100), nullable=True))
    op.add_column('facebook_campaigns', sa.Column('strategy_ids', sa.JSON(), default=[]))
    op.add_column('facebook_campaigns', sa.Column('link_placement', sa.String(20), default='in_post'))
    op.add_column('facebook_campaigns', sa.Column('auto_responder_enabled', sa.Boolean(), default=False))
    op.add_column('facebook_campaigns', sa.Column('auto_responder_type', sa.String(20), default='comment'))
    op.add_column('facebook_campaigns', sa.Column('auto_responder_template', sa.Text(), nullable=True))
    op.add_column('facebook_campaigns', sa.Column('auto_responder_delay_minutes', sa.Integer(), default=5))
    op.add_column('facebook_campaigns', sa.Column('auto_responder_daily_limit', sa.Integer(), default=50))
    
    # Add foreign key for calculator_id
    op.create_foreign_key(
        'fk_facebook_campaigns_calculator_id',
        'facebook_campaigns', 'calculators',
        ['calculator_id'], ['id']
    )
    
    # Add new columns to facebook_posts
    op.add_column('facebook_posts', sa.Column('calculator_id', sa.Integer(), nullable=True))
    op.add_column('facebook_posts', sa.Column('strategy_id', sa.Integer(), nullable=True))
    op.add_column('facebook_posts', sa.Column('first_comment_content', sa.Text(), nullable=True))
    op.add_column('facebook_posts', sa.Column('first_comment_posted', sa.Boolean(), default=False))
    op.add_column('facebook_posts', sa.Column('auto_replies_sent', sa.Integer(), default=0))
    
    # Add foreign keys for facebook_posts
    op.create_foreign_key(
        'fk_facebook_posts_calculator_id',
        'facebook_posts', 'calculators',
        ['calculator_id'], ['id']
    )
    op.create_foreign_key(
        'fk_facebook_posts_strategy_id',
        'facebook_posts', 'post_strategies',
        ['strategy_id'], ['id']
    )


def downgrade():
    # Remove foreign keys from facebook_posts
    op.drop_constraint('fk_facebook_posts_strategy_id', 'facebook_posts', type_='foreignkey')
    op.drop_constraint('fk_facebook_posts_calculator_id', 'facebook_posts', type_='foreignkey')
    
    # Remove columns from facebook_posts
    op.drop_column('facebook_posts', 'auto_replies_sent')
    op.drop_column('facebook_posts', 'first_comment_posted')
    op.drop_column('facebook_posts', 'first_comment_content')
    op.drop_column('facebook_posts', 'strategy_id')
    op.drop_column('facebook_posts', 'calculator_id')
    
    # Remove foreign key from facebook_campaigns
    op.drop_constraint('fk_facebook_campaigns_calculator_id', 'facebook_campaigns', type_='foreignkey')
    
    # Remove columns from facebook_campaigns
    op.drop_column('facebook_campaigns', 'auto_responder_daily_limit')
    op.drop_column('facebook_campaigns', 'auto_responder_delay_minutes')
    op.drop_column('facebook_campaigns', 'auto_responder_template')
    op.drop_column('facebook_campaigns', 'auto_responder_type')
    op.drop_column('facebook_campaigns', 'auto_responder_enabled')
    op.drop_column('facebook_campaigns', 'link_placement')
    op.drop_column('facebook_campaigns', 'strategy_ids')
    op.drop_column('facebook_campaigns', 'calculator_category')
    op.drop_column('facebook_campaigns', 'calculator_mode')
    op.drop_column('facebook_campaigns', 'calculator_id')
    
    # Drop post_strategies table
    op.drop_index('ix_post_strategies_slug', 'post_strategies')
    op.drop_index('ix_post_strategies_id', 'post_strategies')
    op.drop_table('post_strategies')
