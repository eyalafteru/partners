from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# סה"כ בתור
total = db.execute(text('SELECT COUNT(*) FROM scan_queue')).scalar()
print(f'Total in queue: {total}')

# עם calc_id רגיל
with_calc = db.execute(text('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL')).scalar()
print(f'With recommended_calc_id: {with_calc}')

# עם GPT calc_id
with_gpt_calc = db.execute(text('SELECT COUNT(*) FROM scan_queue WHERE gpt_recommended_calc_id IS NOT NULL')).scalar()
print(f'With gpt_recommended_calc_id: {with_gpt_calc}')

# עם כל סוג של calc
with_any = db.execute(text('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL OR gpt_recommended_calc_id IS NOT NULL')).scalar()
print(f'With any calc: {with_any}')

# עם מייל
with_email = db.execute(text("SELECT COUNT(*) FROM scan_queue WHERE owner_email IS NOT NULL AND owner_email != ''")).scalar()
print(f'With email: {with_email}')

db.close()
