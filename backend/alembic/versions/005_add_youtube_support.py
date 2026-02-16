"""Add YouTube support for video posting

Revision ID: 005
Revises: 004
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Add youtube_url to calculators table
    op.add_column('calculators', sa.Column('youtube_url', sa.String(500), nullable=True, comment='URL לסרטון ביוטיוב'))
    
    # Add media_preference to facebook_campaigns
    op.add_column('facebook_campaigns', sa.Column('media_preference', sa.String(20), server_default='image', comment='image/video/both'))
    
    # Add youtube_url to facebook_posts
    op.add_column('facebook_posts', sa.Column('youtube_url', sa.String(500), nullable=True, comment='לינק YouTube בפוסט'))


def downgrade():
    op.drop_column('facebook_posts', 'youtube_url')
    op.drop_column('facebook_campaigns', 'media_preference')
    op.drop_column('calculators', 'youtube_url')
