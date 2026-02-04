"""
Add pipeline_stage for simplified scan workflow

Revision ID: 002
Revises: 001_initial_schema
Create Date: 2026-02-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_pipeline_stage'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add new pipeline tracking columns to scan_queue table.
    
    Pipeline stages:
    - 0: PENDING (URL collected by Apify)
    - 1: SCRAPED (Content scraped by ZenRows)
    - 2: CLASSIFIED (GPT analyzed)
    - 3: WHOIS_DONE (WHOIS lookup completed)
    - 4: LEAD_CREATED (Lead created successfully)
    - 5: FILTERED (Filtered out - bank/insurance/etc)
    - 6: FAILED (Failed after 3 retries)
    """
    
    # Add pipeline_stage column
    op.add_column('scan_queue', sa.Column(
        'pipeline_stage', 
        sa.Integer(), 
        default=0,
        comment='Pipeline stage: 0=pending, 1=scraped, 2=classified, 3=whois_done, 4=lead_created, 5=filtered, 6=failed'
    ))
    
    # Add retry_count column
    op.add_column('scan_queue', sa.Column(
        'retry_count',
        sa.Integer(),
        default=0,
        comment='Number of retry attempts (max 3)'
    ))
    
    # Add stage_updated_at timestamp
    op.add_column('scan_queue', sa.Column(
        'stage_updated_at',
        sa.DateTime(timezone=True),
        comment='When the pipeline stage was last updated'
    ))
    
    # Add index for pipeline_stage for faster queries
    op.create_index('ix_scan_queue_pipeline_stage', 'scan_queue', ['pipeline_stage'])
    
    # Update existing records: set pipeline_stage based on current status
    # This is a data migration to convert old status to new pipeline_stage
    op.execute("""
        UPDATE scan_queue SET pipeline_stage = 
            CASE 
                WHEN status = 'pending' AND html_text IS NULL THEN 0
                WHEN status = 'pending' AND html_text IS NOT NULL AND business_type IS NULL THEN 1
                WHEN status = 'pending' AND business_type IS NOT NULL AND owner_email IS NULL THEN 2
                WHEN status = 'pending' AND owner_email IS NOT NULL THEN 3
                WHEN status = 'matched' THEN 4
                WHEN status = 'discarded' OR is_blacklisted = 1 THEN 5
                WHEN status = 'failed' THEN 6
                ELSE 0
            END,
            retry_count = 0,
            stage_updated_at = CURRENT_TIMESTAMP
        WHERE pipeline_stage IS NULL
    """)


def downgrade():
    """Remove pipeline tracking columns"""
    op.drop_index('ix_scan_queue_pipeline_stage', 'scan_queue')
    op.drop_column('scan_queue', 'stage_updated_at')
    op.drop_column('scan_queue', 'retry_count')
    op.drop_column('scan_queue', 'pipeline_stage')
