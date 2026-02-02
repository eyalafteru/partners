"""
PartnerCalc OS - Default Reply Scenarios
תרחישי תשובות ברירת מחדל למערכת ה-Auto-Reply
"""

DEFAULT_SCENARIOS = [
    {
        "name": "interested_general",
        "display_name": "מעוניין בכללי",
        "category": "positive",
        "keywords": ["מעוניין", "אשמח", "כן", "מצוין", "נשמע טוב"],
        "response_subject": "מצוין! הנה כל מה שצריך להתחיל",
        "response_body": """שלום {{lead_name}},

שמח לשמוע שזה מעניין אותך! 

הנה הקישור לכל המחשבונים שלנו:
https://loan-israel.co.il/category/כלים-ומחשבונים/

יש לך שאלות? אני כאן!

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "how_to_embed",
        "display_name": "איך להטמיע?",
        "category": "positive",
        "keywords": ["איך", "הטמעה", "להטמיע", "וורדפרס", "wordpress", "קוד"],
        "response_subject": "הסבר קצר על הטמעת המחשבון באתר",
        "response_body": """שלום {{lead_name}},

ההטמעה ממש פשוטה! 

3 שלבים בלבד:
1. בחר מחשבון מהרשימה שלנו
2. העתק את קוד הסקריפט
3. הדבק בעמוד שלך

הנה הקישור:
https://loan-israel.co.il/category/כלים-ומחשבונים/

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 95,
        "is_active": True,
    },
    {
        "name": "what_calculators",
        "display_name": "מה יש לכם?",
        "category": "positive",
        "keywords": ["מה יש", "רשימה", "סוגים", "אילו מחשבונים"],
        "response_subject": "הנה כל המחשבונים שלנו",
        "response_body": """שלום {{lead_name}},

יש לנו מגוון גדול של מחשבונים פיננסיים:

מחשבוני הלוואות: החזר הלוואה, משכנתא, השוואת הלוואות
מחשבוני חיסכון: ריבית דריבית, פנסיה, תכנון פרישה
מחשבונים עסקיים: ROI, נקודת איזון, תזרים מזומנים

הכל בחינם:
https://loan-israel.co.il/category/כלים-ומחשבונים/

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 90,
        "is_active": True,
    },
    {
        "name": "specific_request",
        "display_name": "בקשה ספציפית למחשבון",
        "category": "positive",
        "keywords": ["רוצה מחשבון", "יש לכם", "מחפש מחשבון", "צריך מחשבון"],
        "response_subject": "בוא נמצא לך את המחשבון המושלם",
        "response_body": """שלום {{lead_name}},

שמח לעזור!

תספר לי קצת יותר - איזה סוג מחשבון אתה מחפש?

בינתיים הנה כל האוסף שלנו:
https://loan-israel.co.il/category/כלים-ומחשבונים/

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 85,
        "is_active": True,
    },
    {
        "name": "color_customization",
        "display_name": "התאמת עיצוב",
        "category": "positive",
        "keywords": ["צבע", "עיצוב", "התאמה", "לוגו", "מותאם", "מיתוג"],
        "response_subject": "בטח! אפשר להתאים את העיצוב",
        "response_body": """שלום {{lead_name}},

בהחלט אפשר להתאים את העיצוב!

מה אפשר לשנות: צבעים, גופנים, גודל ומיקום, טקסטים

שלח לי את הלוגו/צבעים שלך ואני אכין גרסה מותאמת.

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 80,
        "is_active": True,
    },
    {
        "name": "why_free",
        "display_name": "למה חינם?",
        "category": "question",
        "keywords": ["למה חינם", "קאטצ'", "מלכודת", "מה התמורה"],
        "response_subject": "שאלה טובה! הנה התשובה",
        "response_body": """שלום {{lead_name}},

שאלה מצוינת!

אנחנו עובדים עם בנקים וחברות פיננסיות. כשגולשים משתמשים במחשבונים ומבקשים הצעות - אנחנו מקבלים עמלה.

מה זה אומר בשבילך?
- המחשבון בחינם לחלוטין
- אין התחייבות
- אתה מקבל כלי איכותי

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 75,
        "is_active": True,
    },
    {
        "name": "really_free",
        "display_name": "באמת חינם?",
        "category": "question",
        "keywords": ["באמת חינם", "מחיר", "עלות", "כמה עולה", "תשלום"],
        "response_subject": "כן, באמת חינם!",
        "response_body": """שלום {{lead_name}},

כן, באמת 100% חינם!

אין: דמי הקמה, דמי שימוש חודשיים, עמלות נסתרות
יש: מחשבון מקצועי, תמיכה טכנית, עדכונים שוטפים

פשוט בחר והטמע:
https://loan-israel.co.il/category/כלים-ומחשבונים/

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 70,
        "is_active": True,
    },
    {
        "name": "who_are_you",
        "display_name": "מי אתם?",
        "category": "question",
        "keywords": ["מי אתם", "רק תבקש", "החברה", "מי מאחורי"],
        "response_subject": "קצת עלינו - רק תבקש",
        "response_body": """שלום {{lead_name}},

רק תבקש היא פלטפורמה ישראלית שמחברת בין אנשים למוצרים פיננסיים.

מה אנחנו עושים: מפתחים כלים פיננסיים, עוזרים לאתרים להציע ערך

פועלים בישראל מ-2019, אלפי אתרים משתמשים בכלים שלנו.

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 65,
        "is_active": True,
    },
    {
        "name": "not_now",
        "display_name": "לא עכשיו",
        "category": "deferral",
        "keywords": ["לא עכשיו", "בהמשך", "אחר כך", "לא הזמן", "אולי בעתיד"],
        "response_subject": "בסדר גמור! נשמור קשר",
        "response_body": """שלום {{lead_name}},

אין בעיה בכלל!

הנה הקישור לשמירה:
https://loan-israel.co.il/category/כלים-ומחשבונים/

כשתהיה מוכן - פשוט תחזור אליי.

בהצלחה!

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 50,
        "is_active": True,
    },
    {
        "name": "not_interested",
        "display_name": "לא מעוניין",
        "category": "negative",
        "keywords": ["לא מעוניין", "לא צריך", "לא רלוונטי", "לא מתאים"],
        "response_subject": "תודה על המענה",
        "response_body": """שלום {{lead_name}},

תודה שהקדשת זמן לענות!

אם בעתיד תחפש פתרונות פיננסיים לאתר - אנחנו כאן.

בהצלחה!

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 40,
        "is_active": True,
    },
    {
        "name": "unsubscribe",
        "display_name": "הסרה מרשימת תפוצה",
        "category": "negative",
        "keywords": ["הסר", "הסירו", "ספאם", "תפסיקו", "אל תשלחו"],
        "response_subject": "הוסרת בהצלחה",
        "response_body": """שלום,

הוסרת מרשימת התפוצה שלנו.
לא תקבל יותר הודעות מאיתנו.

מתנצלים על אי הנוחות.

{{sender_name}}
{{sender_title}}""",
        "requires_human": True,
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "platform_question",
        "display_name": "שאלה על פלטפורמה",
        "category": "technical",
        "keywords": ["וויקס", "wix", "שופיפיי", "shopify", "אלמנטור", "elementor"],
        "response_subject": "עובד מצוין על כל פלטפורמה!",
        "response_body": """שלום {{lead_name}},

המחשבונים שלנו עובדים על כל פלטפורמה:
וורדפרס, וויקס, שופיפיי, ג'ומלה, כל אתר HTML

ההטמעה פשוטה: מעתיקים קוד סקריפט קצר ומדביקים בעמוד.

הנה הקישור למחשבונים:
https://loan-israel.co.il/category/כלים-ומחשבונים/

רוצה שאשלח הדרכה ספציפית לפלטפורמה שלך?

{{sender_name}}
{{sender_title}}""",
        "requires_human": False,
        "priority": 60,
        "is_active": True,
    },
    {
        "name": "problem_report",
        "display_name": "דיווח על בעיה",
        "category": "human",
        "keywords": ["לא עובד", "בעיה", "שגיאה", "נתקע", "קרס", "באג"],
        "response_subject": "קיבלתי! בודק מיד",
        "response_body": """שלום {{lead_name}},

תודה שדיווחת!

אני מעביר את זה לצוות הטכני ונחזור אליך בהקדם.

אם יש פרטים נוספים (צילום מסך, קישור לעמוד) - זה יעזור.

{{sender_name}}
{{sender_title}}""",
        "requires_human": True,
        "priority": 110,
        "is_active": True,
    },
    {
        "name": "want_call",
        "display_name": "רוצה לדבר בטלפון",
        "category": "human",
        "keywords": ["טלפון", "לדבר", "להתקשר", "שיחה", "נציג"],
        "response_subject": "בשמחה! מתי נוח לך?",
        "response_body": """שלום {{lead_name}},

בשמחה נדבר!

מתי נוח לך שיחה?
אני זמין בימים א'-ה' בין 09:00-18:00.

שלח לי שעה מועדפת ומספר טלפון, ואתקשר.

{{sender_name}}
{{sender_title}}""",
        "requires_human": True,
        "priority": 105,
        "is_active": True,
    },
    {
        "name": "gpt_fallback",
        "display_name": "תשובה מותאמת אישית (GPT)",
        "category": "fallback",
        "keywords": [],
        "response_subject": "{{gpt_subject}}",
        "response_body": """{{gpt_response}}""",
        "requires_human": True,
        "priority": 1,
        "is_active": True,
        "use_gpt": True,
        "gpt_prompt": """אתה אייל עובדיה, מנהל מקצועי בחברת "רק תבקש" - פלטפורמה ישראלית למחשבונים פיננסיים.

הלקוח שלח הודעה שלא מתאימה לתרחישים המוגדרים. עליך לנסח תשובה מקצועית ואישית.

פרטי הלקוח:
- שם: {{lead_name}}
- דומיין: {{lead_domain}}

ההודעה שלו:
{{trigger_message}}

כללים לתשובה:
1. התייחס ספציפית לבקשה שלו
2. אם מבקש משהו שאין לנו - הסבר בנימוס שאנחנו מתמחים במחשבונים פיננסיים
3. תמיד הצע את המחשבונים שלנו: https://loan-israel.co.il/category/כלים-ומחשבונים/
4. שמור על טון חברי ומקצועי
5. חתום כ: אייל עובדיה, מנהל מקצועי | רק תבקש

נסח נושא מייל מתאים ותשובה מלאה.""",
    },
]


def get_default_scenarios():
    """מחזיר את רשימת התרחישים ברירת מחדל"""
    return DEFAULT_SCENARIOS


def get_scenario_by_name(name: str):
    """מחזיר תרחיש לפי שם"""
    for scenario in DEFAULT_SCENARIOS:
        if scenario["name"] == name:
            return scenario
    return None


def get_scenarios_by_category(category: str):
    """מחזיר תרחישים לפי קטגוריה"""
    return [s for s in DEFAULT_SCENARIOS if s["category"] == category]
