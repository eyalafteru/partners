import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# תבנית 1: הגישה הממוקדת
template1_name = "הגישה הממוקדת"
template1_subject = "שדרוג ה-SEO והערך לגולשים ב-{{domain}}"
template1_body = """היי {{contact_name}},

אני אייל מ"רק תבקש" - פורטל הפיננסים. עברתי על האתרים שלכם ({{domains_only}}) וראיתי פוטנציאל מצוין לשילוב כלים אינטראקטיביים שיכולים להקפיץ את זמן השהייה באתר.

לכבוד 2026, החלטנו לשחרר את כל המחשבונים הפיננסיים שפיתחנו לשימוש חופשי (חינם לגמרי).

💡 למה זה כדאי לך?

• שיפור SEO: גוגל מתה על תוכן אינטראקטיבי (זה מעלה משמעותית את הדירוג)
• חוויית משתמש: הגולשים מקבלים ערך מיידי ({{calculators_list}}) ונשארים יותר זמן בדף
• התאמה מלאה: המחשבונים רספונסיביים וניתן להתאים את הצבעים שלהם למותג שלכם בקליק

👉 אפשר לראות את כולם ולהטמיע מכאן: https://loan-israel.co.il/calculators

✨ חסר לך מחשבון ספציפי?

תענה לי למייל הזה. אם הרעיון מתאים, נפתח אותו עבורך בחינם תוך 10 ימי עסקים.

בברכה,
אייל עובדיה
רק תבקש | loan-israel.co.il"""

# עדכון תבנית 1
c.execute('''UPDATE email_templates 
             SET name = ?, subject = ?, body_text = ?, body_html = ?
             WHERE id = 1''', 
          (template1_name, template1_subject, template1_body, template1_body))

print(f'✅ עודכנה תבנית 1: {template1_name}')

# תבנית 2: בנימה אישית
template2_name = "בנימה אישית"
template2_subject = "משהו קטן (וחינמי) שיכול לעזור ל-{{domain}}"
template2_body = """היי,

נתקלתי באתרים שלך ({{domains_only}}) וממש אהבתי את התוכן.

אני אייל מ"רק תבקש", ולכבוד השנה החדשה פתחנו לקהל הרחב עשרות מחשבונים פיננסיים שפיתחנו. חשבתי ש{{calculators_list}} יכולים לשבת אצלך בול ולחסוך לגולשים שלך המון כאב ראש (ולך אלפי שקלים על פיתוח).

זה פשוט להטמעה כמו סרטון יוטיוב, רספונסיבי לחלוטין, ואפשר לשנות צבעים שיתאימו לעיצוב שלך.

👉 אפשר להציץ כאן: https://loan-israel.co.il/calculators

ואם יש מחשבון שאתה צריך ואין לנו - רק תבקש. נשמח לפתח אותו עבורך (ללא עלות).

בהצלחה!
אייל"""

# יצירת תבנית 2
c.execute('''INSERT INTO email_templates (name, subject, body_text, body_html, category, is_active)
             VALUES (?, ?, ?, ?, ?, ?)''',
          (template2_name, template2_subject, template2_body, template2_body, 'outreach', 1))

print(f'✅ נוצרה תבנית 2: {template2_name}')

conn.commit()
conn.close()

print('\n📧 שתי התבניות מוכנות!')
