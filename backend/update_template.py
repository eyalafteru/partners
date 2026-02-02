import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Better sales template
body_text = """שלום,

שמי אייל מהלוואות ישראל.

ראיתי שיש לכם אתרים בתחום הפיננסי ורציתי להציע שיתוף פעולה.

אנחנו מפתחים מחשבונים פיננסיים מתקדמים שמגדילים את זמן השהייה באתר ומשפרים את ה-SEO.

לאתרים שלכם אני ממליץ על:
{{domains_list}}

המחשבונים שלנו מותאמים למובייל, עם קוד הטמעה פשוט ועיצוב מקצועי.

אשמח לשלוח לכם דוגמא חיה - פשוט ענו למייל הזה.

בברכה,
אייל
הלוואות ישראל
050-1234567
loan-israel.co.il"""

body_html = """<div dir="rtl" style="font-family: Assistant, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.8;">

<p>שלום,</p>

<p>שמי <strong>אייל</strong> מהלוואות ישראל.</p>

<p>ראיתי שיש לכם אתרים בתחום הפיננסי ורציתי להציע שיתוף פעולה.</p>

<p>אנחנו מפתחים <strong style="color: #1e5490;">מחשבונים פיננסיים מתקדמים</strong> שמגדילים את זמן השהייה באתר ומשפרים את ה-SEO.</p>

<div style="background: #f8fafc; padding: 15px 20px; border-radius: 8px; margin: 20px 0; border-right: 4px solid #1e5490;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #1e5490;">לאתרים שלכם אני ממליץ על:</p>
{{domains_list}}
</div>

<p>המחשבונים שלנו מותאמים למובייל, עם קוד הטמעה פשוט ועיצוב מקצועי.</p>

<p style="background: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center;">
<strong>אשמח לשלוח לכם דוגמא חיה - פשוט ענו למייל הזה</strong>
</p>

<p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
בברכה,<br>
<strong>אייל</strong><br>
הלוואות ישראל<br>
050-1234567<br>
<a href="https://loan-israel.co.il" style="color: #1e5490;">loan-israel.co.il</a>
</p>
</div>"""

c.execute('''
UPDATE email_templates 
SET name = ?,
    subject = ?,
    body_text = ?,
    body_html = ?,
    variables = ?,
    updated_at = ?
WHERE id = 1
''', (
    'הצעת שיתוף פעולה - מחשבונים פיננסיים',
    'הצעת שיתוף פעולה - מחשבונים לאתרים שלכם',
    body_text,
    body_html,
    json.dumps(['domains_list']),
    datetime.now().isoformat()
))

print('✅ Template updated!')
conn.commit()
conn.close()
