import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Template based on actual landing page content
body_text = """שלום,

רוצים להטמיע מחשבון פיננסי באתר שלכם? חינם לחלוטין!

ראיתי את האתרים שלכם:
{{domains_list}}

אני נותן לכם מחשבון מקצועי עם 5 טאבים, חישובים מדויקים, ועיצוב responsive מלא.
תמורת קישור קרדיט קטן לאתר שלנו - תקבלו מחשבון ששווה מעל 15,000 ש"ח בפיתוח.

למה כדאי להטמיע מחשבון באתר שלכם?
✅ תוכן אינטראקטיבי איכותי - גוגל אוהבת!
✅ זמן שהייה ארוך יותר באתר = SEO טוב יותר
✅ Mobile Friendly - עובד מצוין במובייל
✅ הקטנת Bounce Rate

ההטמעה לוקחת 3 דקות בלבד - פשוט מעתיקים קוד.

רק תבקש ואשלח לך את הקוד!

אייל
הלוואות ישראל
loan-israel.co.il"""

body_html = """<div dir="rtl" style="font-family: Assistant, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.8;">

<h2 style="color: #1e5490; text-align: center;">🎁 רוצים להטמיע מחשבון פיננסי באתר שלכם?<br>חינם לחלוטין!</h2>

<p>שלום,</p>

<p>ראיתי את האתרים שלכם:</p>

<div style="background: #f0f7ff; padding: 15px 20px; border-radius: 8px; margin: 15px 0;">
{{domains_list}}
</div>

<p>💎 אני נותן לכם <strong>מחשבון מקצועי</strong> עם 5 טאבים, חישובים מדויקים, ועיצוב responsive מלא.</p>

<p>תמורת קישור קרדיט קטן לאתר שלנו - תקבלו מחשבון ש<strong style="color: #1e5490;">שווה מעל 15,000 ש"ח</strong> בפיתוח.</p>

<div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0 0 10px 0; font-weight: bold;">🚀 למה כדאי להטמיע מחשבון באתר?</p>
<ul style="margin: 0; padding-right: 20px;">
<li>✅ תוכן אינטראקטיבי איכותי - גוגל אוהבת!</li>
<li>✅ זמן שהייה ארוך יותר = SEO טוב יותר</li>
<li>✅ Mobile Friendly - עובד מצוין במובייל</li>
<li>✅ הקטנת Bounce Rate</li>
</ul>
</div>

<p>📋 ההטמעה לוקחת <strong>3 דקות בלבד</strong> - פשוט מעתיקים קוד.</p>

<div style="background: #c8e6c9; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
<p style="margin: 0; font-size: 18px; font-weight: bold;">👆 רק תבקש ואשלח לך את הקוד!</p>
</div>

<p style="margin-top: 30px; color: #666;">
אייל<br>
<strong>הלוואות ישראל</strong><br>
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
    'רק תבקש - מחשבון חינם',
    '🎁 מחשבון פיננסי חינם לאתר שלכם - רק תבקש!',
    body_text,
    body_html,
    json.dumps(['domains_list']),
    datetime.now().isoformat()
))

print('✅ Template updated with "רק תבקש" message!')
conn.commit()
conn.close()
