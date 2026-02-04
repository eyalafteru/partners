"""Add missing columns to facebook_campaigns and facebook_posts"""

from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://partnercalc:partnercalc123@49.13.31.182:3306/partnercalc')

with engine.connect() as conn:
    # Add missing columns to facebook_campaigns
    campaigns_columns = [
        "ALTER TABLE facebook_campaigns ADD COLUMN calculator_id INT NULL",
        "ALTER TABLE facebook_campaigns ADD COLUMN calculator_mode VARCHAR(20) DEFAULT 'all'",
        "ALTER TABLE facebook_campaigns ADD COLUMN calculator_category VARCHAR(100) NULL",
        "ALTER TABLE facebook_campaigns ADD COLUMN strategy_ids JSON DEFAULT NULL",
        "ALTER TABLE facebook_campaigns ADD COLUMN link_placement VARCHAR(20) DEFAULT 'in_post'",
        "ALTER TABLE facebook_campaigns ADD COLUMN auto_responder_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE facebook_campaigns ADD COLUMN auto_responder_type VARCHAR(20) DEFAULT 'comment'",
        "ALTER TABLE facebook_campaigns ADD COLUMN auto_responder_template TEXT NULL",
        "ALTER TABLE facebook_campaigns ADD COLUMN auto_responder_delay_minutes INT DEFAULT 5",
        "ALTER TABLE facebook_campaigns ADD COLUMN auto_responder_daily_limit INT DEFAULT 50",
    ]
    
    # Add missing columns to facebook_posts
    posts_columns = [
        "ALTER TABLE facebook_posts ADD COLUMN calculator_id INT NULL",
        "ALTER TABLE facebook_posts ADD COLUMN strategy_id INT NULL",
        "ALTER TABLE facebook_posts ADD COLUMN first_comment_content TEXT NULL",
        "ALTER TABLE facebook_posts ADD COLUMN first_comment_posted BOOLEAN DEFAULT FALSE",
        "ALTER TABLE facebook_posts ADD COLUMN auto_replies_sent INT DEFAULT 0",
    ]
    
    for sql in campaigns_columns + posts_columns:
        try:
            conn.execute(text(sql))
            print(f'✅ OK: {sql[:70]}...')
        except Exception as e:
            if 'Duplicate column' in str(e):
                print(f'⏭️ Already exists: {sql.split("COLUMN ")[1].split(" ")[0]}')
            else:
                print(f'❌ ERROR: {sql[:50]}... - {e}')
    
    conn.commit()
    print('\n✅ Done!')
