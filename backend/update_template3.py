import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Human, personal template
body_text = """היי,

אני אייל מ"הלוואות ישראל" - אתר הפיננסים המוביל בישראל.

לכבוד 2026 החלטנו לעשות את השנה הזו שנת נתינה 🎁
ולכן פיתחנו עשרות מחשבונים פיננסיים שאפשר להטמיע בקליק בכל אתר.

מגלישה ברשת נתקלתי באתרים שלך:
{{domains_list}}

ומצאתי שיש לנו מחשבונים שיכולים להתאים לך בול!

למה שווה לך להטמיע מחשבון?
• גוגל אוהבת תוכן אינטראקטיבי - זה משפר את הדירוג שלך
• גולשים נשארים יותר זמן באתר כשיש להם כלי שימושי
• זה נראה מקצועי ומוסיף אמינות לאתר
• חוסך לך אלפי שקלים בפיתוח

איך עושים את זה?
פשוט חפש בגוגל: "רק תבקש מחשבונים"
תבחר את המחשבון שמתאים לך ובלחיצת כפתור תטמיע אותו באתר.

רוצה מחשבון שעדיין לא קיים אצלנו?
השב למייל הזה עם הרעיון שלך - ותוך 10 ימי עסקים נפתח לך מחשבון מותאם אישית, בחינם!

בהצלחה,
אייל
הלוואות ישראל
loan-israel.co.il"""

body_html = """<div dir="rtl" style="font-family: Assistant, Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.9; color: #333;">

<p>היי,</p>

<p>אני אייל מ<strong>"הלוואות ישראל"</strong> - אתר הפיננסים המוביל בישראל.</p>

<p>לכבוד 2026 החלטנו לעשות את השנה הזו <strong style="color: #1e5490;">שנת נתינה</strong> 🎁<br>
ולכן פיתחנו עשרות מחשבונים פיננסיים שאפשר להטמיע בקליק בכל אתר.</p>

<p>מגלישה ברשת נתקלתי באתרים שלך:</p>

<div style="background: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin: 15px 0; border-right: 3px solid #1e5490;">
{{domains_list}}
</div>

<p>ומצאתי שיש לנו מחשבונים שיכולים להתאים לך בול!</p>

<div style="background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0 0 15px 0; font-weight: bold; color: #2e7d32;">💡 למה שווה לך להטמיע מחשבון?</p>
<ul style="margin: 0; padding-right: 25px; line-height: 2;">
<li>גוגל אוהבת תוכן אינטראקטיבי - זה משפר את הדירוג שלך</li>
<li>גולשים נשארים יותר זמן באתר כשיש להם כלי שימושי</li>
<li>זה נראה מקצועי ומוסיף אמינות לאתר</li>
<li>חוסך לך אלפי שקלים בפיתוח</li>
</ul>
</div>

<div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #e65100;">🔍 איך עושים את זה?</p>
<p style="margin: 0;">פשוט חפש בגוגל: <strong style="color: #1e5490;">"רק תבקש מחשבונים"</strong><br>
תבחר את המחשבון שמתאים לך ובלחיצת כפתור תטמיע אותו באתר.</p>
</div>

<div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #1565c0;">✨ רוצה מחשבון שעדיין לא קיים אצלנו?</p>
<p style="margin: 0;">השב למייל הזה עם הרעיון שלך - ותוך <strong>10 ימי עסקים</strong> נפתח לך מחשבון מותאם אישית, בחינם!</p>
</div>

<p style="margin-top: 30px;">
בהצלחה,<br>
<strong>אייל</strong><br>
הלוואות ישראל<br>
<a href="https://loan-israel.co.il" style="color: #1e5490; text-decoration: none;">loan-israel.co.il</a>
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
    'שנת הנתינה 2026 - מחשבונים בחינם',
    '🎁 שנת הנתינה 2026 - מחשבונים פיננסיים בחינם לאתר שלך',
    body_text,
    body_html,
    json.dumps(['domains_list']),
    datetime.now().isoformat()
))

print('✅ Template updated - human & personal!')
conn.commit()
conn.close()
