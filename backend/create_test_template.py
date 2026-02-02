import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Create test template
body_html = '''<div dir="rtl" style="font-family: Assistant, Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<p>שלום {{contact_name}},</p>

<p>ראיתי את האתר <strong>{{domain}}</strong> ושמתי לב שאתם עוסקים בתחום הפיננסי.</p>

<p>יש לנו <strong style="color: #1e5490;">{{calculator_name}}</strong> שיכול להתאים מצוין לאתר שלכם ולהגדיל המרות.</p>

<div style="background: #f0f7ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0; font-weight: bold;">המחשבון שלנו:</p>
<ul style="margin: 10px 0;">
<li>מותאם לנייד</li>
<li>קל להטמעה (קוד אחד!)</li>
<li>14 ימי ניסיון חינם</li>
</ul>
</div>

<p>רוצה לשמוע עוד?</p>

<p style="margin-top: 30px;">
בברכה,<br>
<strong>{{my_name}}</strong><br>
{{my_company}}<br>
טלפון: {{my_phone}}
</p>
</div>'''

body_text = '''שלום {{contact_name}},

ראיתי את האתר {{domain}} ושמתי לב שאתם עוסקים בתחום הפיננסי.

יש לנו {{calculator_name}} שיכול להתאים מצוין לאתר שלכם ולהגדיל המרות.

המחשבון שלנו:
- מותאם לנייד
- קל להטמעה (קוד אחד!)
- 14 ימי ניסיון חינם

רוצה לשמוע עוד?

בברכה,
{{my_name}}
{{my_company}}
{{my_phone}}'''

c.execute('''
INSERT INTO email_templates (name, subject, body_text, body_html, variables, category, is_active, usage_count, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'הצעת שיתוף פעולה - מחשבון פיננסי',
    'הזדמנות ל{{site_name}} - {{calculator_name}} בחינם!',
    body_text,
    body_html,
    json.dumps(['domain', 'site_name', 'contact_name', 'calculator_name', 'my_name', 'my_company', 'my_phone']),
    'first_contact',
    1,
    0,
    datetime.now().isoformat(),
    datetime.now().isoformat()
))

template_id = c.lastrowid
print(f'✅ Created template ID: {template_id}')

conn.commit()
conn.close()
print('Done!')
