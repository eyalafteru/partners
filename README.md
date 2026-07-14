# PartnerCalc OS 🧮

מערכת אוטומטית לניהול שותפויות מחשבונים - מציאת שותפים, התאמת תוכן פיננסי, יצירת Backlinks איכותיים.

## 🎯 יכולות המערכת

### יכולות ליבה
- **Lead Hunter** - סריקה אוטומטית של תוצאות Google עם Apify
- **AI Matching** - התאמת מחשבונים לאתרים באמצעות DictaLM (עברית)
- **Multi-Channel Outreach** - WhatsApp, Email, SMS
- **Auto-Reply** - תגובות אוטומטיות חכמות מבוססות AI
- **Watchdog** - מעקב אחר התקנות והתראות
- **Dashboard** - לוח בקרה מלא עם סטטיסטיקות בזמן אמת

### 🆕 פיצ'רים חדשים שנבנו

#### 🔍 סריקה וניתוח
- **Apify Google Scraper** - סריקה של 50-200 תוצאות לכל שאילתה
- **HTML Scraping** - שליפת תוכן נקי מכל עמוד (עד 10,000 תווים)
- **WHOIS Lookup** - חילוץ פרטי בעלים, ארגון ומייל מדומיין
- **דפדוף תוצאות** - טעינה אסינכרונית של 100 דומיינים בכל עמוד

#### 🤖 AI Classification (סיווג עסקים)
- **סיווג חכם** - זיהוי סוג עסק: בנק, ביטוח, תאגיד, פינטק, עסק קטן, אתר לידים, אתר תוכן
- **Batch AI Processing** - ניתוח מקבילי של עשרות אתרים
- **GPU Loading/Unloading** - ניהול זיכרון GPU עם כפתורי שליטה
- **תהליך חשיבה** - שמירת הנמקת AI לכל סיווג
- **Real-time Progress** - צפייה בניתוח AI בזמן אמת (דומיין נוכחי, התקדמות)

#### 📊 ממשק משתמש מתקדם
- **סינון מתקדם** - פילטרים לפי סטטוס, סוג עסק, האם נותח
- **Content Viewer Modal** - צפייה בתוכן שנשלח ל-AI (עם הדגשת מיילים/טלפונים)
- **טבלת דומיינים מאוחדת** - כל הדומיינים מכל הסריקות עם favicon
- **אינדיקטורים בזמן אמת** - נקודה ירוקה מהבהבת לסריקה פעילה
- **Progress Bars** - התקדמות סריקה וניתוח AI

#### ⚡ שיפורי ביצועים
- **טעינה אסינכרונית** - הממשק לא נתקע בזמן סריקה/ניתוח
- **Timeouts חכמים** - 5 שניות לקריאות API
- **Auto-refresh** - רענון אוטומטי כל 10 שניות בזמן סריקה

## 🛠️ טכנולוגיות

### Backend
- **FastAPI** - Python 3.11+
- **SQLite** (פיתוח) / **PostgreSQL** (production)
- **Celery + Redis** - משימות רקע
- **Ollama + DictaLM-3 Thinking** - AI מקומי לעברית עם תמיכת GPU

### Frontend
- **Next.js 14** - React Framework
- **Tailwind CSS** - עיצוב
- **TypeScript**
- **Lucide Icons** - אייקונים

### Scraping
- **Apify** - Google Search Scraper
- **httpx** - Async HTTP Client
- **BeautifulSoup** - HTML Parsing
- **python-whois** - WHOIS Lookup

## 📁 מבנה הפרויקט

```
partnercalc-os/
├── backend/                 # Python FastAPI
│   ├── app/
│   │   ├── api/            # API Routes
│   │   │   ├── scans.py    # 🆕 סריקות + AI Analysis
│   │   │   ├── leads.py    # לידים
│   │   │   ├── stats.py    # סטטיסטיקות
│   │   │   └── admin/      # ניהול
│   │   ├── models/         # SQLAlchemy Models
│   │   │   ├── scan_campaign.py  # 🆕 ScanQueue עם business_type
│   │   │   └── ...
│   │   ├── services/       # Business Logic
│   │   ├── tasks/          # Celery Tasks
│   │   ├── ai/             # Ollama Integration
│   │   │   ├── ollama_client.py  # 🆕 GPU Load/Unload
│   │   │   └── prompts_manager.py
│   │   └── scraper/        # Scraping Logic
│   │       ├── apify_client.py
│   │       ├── apify_html_scraper.py  # 🆕 HTML + WHOIS
│   │       └── whois_lookup.py        # 🆕 WHOIS
│   ├── alembic/            # Migrations
│   └── requirements.txt
├── frontend/                # Next.js Dashboard
│   ├── app/
│   │   ├── scans/          # 🆕 מסך סריקות מלא
│   │   │   └── page.tsx    # סריקות + AI + פילטרים
│   │   ├── leads/          # לידים
│   │   ├── dashboard/      # Dashboard
│   │   └── admin/          # ניהול
│   ├── components/
│   └── styles/
├── docker/                  # Docker Compose
└── scripts/                 # Setup Scripts
```

## 🚀 התקנה

### דרישות מקדימות
- Python 3.11+
- Node.js 20+
- Ollama (עם מודל DictaLM)
- Docker (אופציונלי - ל-Celery)

### שלבים

1. **בדיקת סביבה**
```bash
scripts\check-environment.bat
```

2. **התקנה מלאה**
```bash
scripts\setup.bat
```

3. **הפעלת פיתוח**
```bash
scripts\start-dev.bat
```

4. **הפעלת Celery Workers (אופציונלי)**
```bash
cd docker
docker-compose -f docker-compose.dev.yml up
```

## 📡 API Endpoints

### סריקות (🆕 מורחב)
| Endpoint | תיאור |
|----------|--------|
| `GET /api/scans` | רשימת סריקות |
| `POST /api/scans` | יצירת סריקה חדשה |
| `GET /api/scans/{id}/results` | תוצאות סריקה |
| `GET /api/scans/domains/all` | 🆕 כל הדומיינים מכל הסריקות |
| `POST /api/scans/{id}/analyze` | 🆕 ניתוח HTML + WHOIS |
| `POST /api/scans/{id}/classify-ai` | 🆕 סיווג AI לכל האתרים |
| `POST /api/scans/classify-selected` | 🆕 סיווג AI לאתרים נבחרים |
| `GET /api/scans/{id}/ai-stats` | 🆕 סטטיסטיקות AI בזמן אמת |

### AI & GPU (🆕)
| Endpoint | תיאור |
|----------|--------|
| `POST /api/ai/load-gpu` | 🆕 טעינת מודל ל-GPU |
| `POST /api/ai/unload-gpu` | 🆕 שחרור זיכרון GPU |
| `GET /api/ai/gpu-status` | 🆕 סטטוס GPU (טעון/לא) |

### כללי
| Endpoint | תיאור |
|----------|--------|
| `GET /api/health` | בדיקת תקינות |
| `GET /api/calculators` | רשימת מחשבונים |
| `GET /api/leads` | רשימת לידים |
| `GET /api/stats/dashboard` | סטטיסטיקות Dashboard |
| `GET /api/prompts` | רשימת פרומפטים |
| `GET /api/admin/database/tables` | Database Explorer |

## 🎨 מסכי Dashboard

- **Dashboard** - סטטיסטיקות ו-Funnel
- **מחשבונים** - ניהול ספריית המחשבונים
- **לידים** - ניהול לידים וסטטוסים
- **סריקות** - 🆕 יצירה, ניתוח AI, סינון מתקדם
- **הודעות** - Unified Inbox
- **פרומפטים** - ניהול 9 צמתי AI
- **Auto-Reply** - הגדרות תגובה אוטומטית
- **API Keys** - ניהול טוקנים (מוצפן)
- **Database** - Explorer למסד נתונים

## 🔐 הגדרות

צור קובץ `.env` בתיקיית `backend`:

```env
# Database (already configured for remote server)
DB_HOST=185.151.198.29
DB_PORT=35432
DB_USER=postgresql_ppcmedia
DB_PASSWORD=pwaTaRA8SfHaDDp2
DB_NAME=partnercalc

# Ollama
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=dicta-llm-3

# WhatsApp (Green-API)
GREENAPI_INSTANCE_ID=your_instance_id
GREENAPI_TOKEN=your_token

# Email (SendGrid)
SENDGRID_API_KEY=your_api_key

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+972...

# Apify
APIFY_API_TOKEN=your_token
```

### פרסום אוטומטי של תגובות בפייסבוק (דפדפן מקומי)

כדי ש"אשר" יפרסם תגובה אוטומטית בפייסבוק, צריך להגדיר דפדפן מקומי (Playwright).  
**מדריך מלא:** `partners/backend/BROWSER-SETUP.md`

**בקצרה:**
1. `pip install playwright` ואז `playwright install chromium`
2. Cookie פייסבוק ב-DB (העלאה בממשק) או ב-.env כ־`FACEBOOK_COOKIE`
3. הבקנד רץ על מחשב עם מסך (לא שרת מרוחק) – ייפתח חלון Chrome לפרסום

## 📊 AI Nodes (צמתי AI)

1. **filter_real_business** - סינון עסקים אמיתיים
2. **match_calculator** - התאמת מחשבון
3. **extract_contact** - חילוץ פרטי קשר
4. **draft_whatsapp** - ניסוח הודעת WhatsApp
5. **draft_email** - ניסוח Email
6. **draft_sms** - ניסוח SMS
7. **analyze_response** - ניתוח תגובה
8. **suggest_reply** - הצעת תשובה
9. **identify_form_fields** - זיהוי שדות טופס

### 🆕 סיווג עסקים (Business Type Classification)

ה-AI מסווג כל אתר לאחת מהקטגוריות:

| סוג | אייקון | תיאור | פוטנציאל |
|-----|--------|--------|----------|
| `lead_site` | 🎯 | אתר לידים | ⭐⭐⭐ גבוה |
| `small_business` | 💼 | עסק קטן | ⭐⭐⭐ גבוה |
| `content_site` | 📰 | אתר תוכן | ⭐⭐ בינוני |
| `bank` | 🏦 | בנק | ⭐ נמוך |
| `insurance` | 🛡️ | ביטוח | ⭐ נמוך |
| `corporation` | 🏢 | תאגיד | ⭐ נמוך |
| `fintech` | 🚀 | פינטק | ⭐⭐ בינוני |
| `private` | 🏪 | פרטי | ⭐⭐ בינוני |

## 🔄 זרימת העבודה

```
1. יצירת סריקה (מילות מפתח)
         ↓
2. Apify מביא 100-200 URLs
         ↓
3. ⚡ נתח אתרים (HTML + WHOIS)
         ↓
4. 🤖 סיווג AI (סוג עסק)
         ↓
5. סינון לפי סוג (לידים/עסק קטן)
         ↓
6. Outreach (WhatsApp/Email/SMS)
         ↓
7. AI עונה לתגובות
         ↓
8. Watchdog עוקב אחר התקנות
```

## 🐛 בעיות ידועות / מצב פיתוח

### ⚠️ איפה הסוכן נתקע (סוף השיחה)
ה-Backend נתקע ב-timeout בזמן טעינת תוצאות סריקה. 

**לפתרון:**
```bash
# 1. הרוג את התהליך התקוע
taskkill /F /IM python.exe

# 2. הפעל מחדש את השרת
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

**שיפורים אפשריים:**
- הוספת pagination צד-שרת לכל ה-endpoints
- הגבלת כמות תוצאות ל-50 בכל קריאה
- הוספת caching לתוצאות סריקה

### 📋 רשימת משימות להמשך
- [ ] תיקון timeout בטעינת תוצאות
- [ ] הוספת Outreach (שליחת הודעות)
- [ ] הוספת Unified Inbox
- [ ] הוספת Watchdog למעקב התקנות
- [ ] הוספת Auto-Reply

---

## 🖥️ שרת ייצור (Production Server)

| פרמטר | ערך |
|-------|-----|
| **IP** | `49.13.31.182` |
| **SSH Port** | `22` |
| **SSH User** | `root` |
| **גישת SSH** | מפתח SSH מוגדר (ללא סיסמה) |
| **דומיין** | `partners.ppcmedia.co.il` |
| **נתיב הפרויקט** | `/opt/partnercalc-os/` |
| **Docker Compose** | `docker/docker-compose.prod.yml` |

### 🗄️ בסיס נתונים (ייצור)

| פרמטר | ערך |
|-------|-----|
| **DB Host** | `mariadb` (רשת Docker פנימית) |
| **DB Name** | `partnercalc` |
| **DB User** | `partnercalc` |
| **DB Password** | `partnercalc123` |
| **DB Host חיצוני** | `49.13.31.182:3306` |

### 🚀 פריסה לייצור (Deployment)

```bash
# 1. מהמחשב המקומי - Push לגיטהאב
git add .
git commit -m "your message"
git push origin main

# 2. SSH לשרת (ללא סיסמה - מפתח SSH)
ssh root@49.13.31.182

# 3. בשרת - משוך קוד חדש
cd /opt/partnercalc-os
git pull origin main

# 4. הרץ migrations חדשים
cd backend && python -m alembic upgrade head && cd ..

# 5. ריסטארט הבאקנד
docker-compose -f docker/docker-compose.prod.yml restart backend

# 6. בדוק שהכל עובד
curl http://localhost:8000/api/health
curl https://partners.ppcmedia.co.il/api/lead-hunter/categories
```

### 🔑 מפתחות API בשרת

עדכן `/opt/partnercalc-os/backend/.env` עם:

```env
# AI - Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# WhatsApp - Green API
GREENAPI_INSTANCE_ID=7105206891
GREENAPI_API_TOKEN=20fdcb013dd3423e845cba372e6886996bf7246ed39d4b9c89
GREENAPI_URL=https://7105.api.greenapi.com
```

### 📡 Lead Hunter - Google Apps Script

הסקריפט נמצא ב: `scripts/lead_hunter_sheets.gs`

- **גיליון Apps Script (ישן)**: [all_posts](https://docs.google.com/spreadsheets/d/1gwwBf6-7cqEerBdg8ZhyeXsuy9tlGwVD8ROJiRfIhl8)
- **גיליון פושר (מקור הנתונים)**: [Posts](https://docs.google.com/spreadsheets/d/1Xbor7YEr_apjvmQZ9QYU01UKwKk_EKqlUTH_7C69LIU/edit?gid=128669743#gid=128669743)
  - גיליון `posts` -- פושר כותב לכאן פוסטים מקבוצות פייסבוק
  - עמודות: url, description, group_name, group_url, author_name, author_url, posted_at, created_at, sent
- **שורת התחלה**: 171 (שורות 1-170 הן נתונים ישנים)
- **תדירות**: כל 5 דקות אוטומטית
- **Token**: `lead-hunter-secret-2024`

---

## 💬 אסטרטגיית תגובות בפייסבוק

### מצב נוכחי (יוני 2026): טקסט בלבד, מגבלה הדרגתית
- תגובות **קצרות** (משפט אחד), **ללא לינקים**, **ללא תמונות**, **ללא מספרי טלפון**
- חשבון: **משה עובדיה** (מחובר דרך Brave + Chrome Extension)
- סגנון: המלצה טבעית על "הובלות בישראל", עם "תכתבי/תכתוב לי בפרטי"
- עדיפות לפוסטים מאזור **מרכז** (מובנה בקוד `PRIORITY_AREA`)

### מגבלה יומית הדרגתית (DAILY_LIMIT_SCHEDULE)
הופעלה ב-9 ביוני 2026. הספירה מתחילה מ-`updated_at` של הקטגוריה:
- **שבוע 1** (ימים 1-7): 3-5 תגובות ביום (מספר אקראי-יציב לכל יום)
- **שבוע 2** (ימים 8-14): 5-10 תגובות ביום
- **שבוע 3+** (ימים 15+): 8-15 תגובות ביום
- קובץ: `backend/app/tasks/lead_hunter_tasks.py`

### הגנות בטיחות
- מרווח 8-15 דקות בין תגובות (`MIN_GAP_BETWEEN_REPLIES_MIN` / `MAX_GAP_BETWEEN_REPLIES_MIN`)
- שעות פעילות 07:00-23:00 שעון ישראל (`ISRAEL_UTC_OFFSET = 3` בקיץ, 2 בחורף)
- מקסימום 3 משימות pending בו-זמנית
- הגנת כפילויות (לא מגיב פעמיים לאותו URL)
- פוסטים עד 48 שעות אחורה בלבד
- delay של 15 דקות לפני תגובה (כדי להיראות טבעי)
- התראת WhatsApp כש-Brave לא פעיל (20 דקות)

### סינון פוסטים רגישים (SKIP_REPLY_KEYWORDS)
פוסטים עם מילות מפתח רגישות לא מקבלים תגובה אוטומטית:
- תרומות, צדקה, גיוס כספים, עזרה דחופה
- הלום קרב, חיילים בודדים, עולים חדשים
- הלוויה, שבעה, אבל, נפטר
- למסירה, אשמח לעזרה
- קובץ: `backend/app/services/lead_hunter_service.py`

### סיווג AI - כללים חשובים
- מי שקונה מוצר עם משלוח (דלתות, רהיטים) = "לא רלוונטי", לא הובלה
- ספאמרים שמפרסמים את עצמם = קטגוריה 4 (מתחרה)
- קובץ: `backend/app/services/lead_hunter_service.py` (SYSTEM_PROMPT)

### קבוצות חסומות (BLOCKED_GROUPS)
בדיקה ברמת הקוד -- פוסטים מקבוצות חסומות מסומנים אוטומטית כ-`group_blocked`:
- `1629283237109586` -- הובלות, מובילים ממומלצים, חיפוש מובילים
- `BeerShevaTogether` -- באר שבע ביחד
- `186182019096864` -- דלתות פנים במחירי חיסול
- קובץ: `backend/app/tasks/lead_hunter_tasks.py`

### הודעות WhatsApp
- כל תגובה שנכנסת לתור שולחת הודעת וואצאפ לסקירה ל-`0542575412` עם:
  - פרטי הפוסט, קבוצה, אזור
  - התגובה שפורסמה
  - **לינק לפוסט**
- התראה כש-Brave תקוע (pending > 20 דקות)

### סטטוסים בממשק (auto_reply_status)
| סטטוס | צבע | משמעות |
|--------|------|---------|
| `pending` | צהוב | ממתין לפרסום |
| `working` | כחול | מפרסם כרגע |
| `posted` / `sent` | ירוק | פורסם בהצלחה |
| `failed` | אדום | נכשל |
| `group_blocked` | אפור | קבוצה חסומה |
| `skipped` | - | דולג (כפילות/ידני) |

### באנרים (מושבת זמנית - שמור לעתיד)
תמונות באנר מוכנות בתיקייה `chrome-extension/banners/`:
- `savings.png` - באנר חיסכון ("חסכו עד 40%")
- `trust.png` - באנר אמינות ("מובילים מאומתים")
- לוגיקה מושבתת ב-`lead_hunter_service.py` (מסומנת כהערה)
- DB columns: `lead_posts.reply_type`, `lead_posts.banner_type`
- **להפעלה מחדש:** הסר הערות מהבלוק ב-`classify_and_notify_background`

### היסטוריית חסימות
| תאריך | אירוע | פעולה |
|--------|--------|--------|
| מרץ 2026 | תגובות Pending בקבוצות מרובות | הורדת לינקים ומספרי טלפון מהתגובות |
| מאי 2026 | באנר+לינק = Pending מיידי | כיבוי באנרים, חזרה לטקסט בלבד |
| 12 מאי | הפעלת 10/יום, עבד טוב | שבוע של פרסום מוצלח |
| 1 יוני | חסימה מלאה "You can't use this feature" | עצירה מלאה |
| 9 יוני | הפעלה מחדש 3-5/יום זהירה | מגבלה הדרגתית חדשה |

---

## ⚠️ גיליון פושר - שורות ריקות
שורות ריקות בגיליון נגמרות = הפושר מפסיק לכתוב = המערכת לא מקבלת לידים חדשים.
**קרה כבר פעמיים** (17 מאי, 17 יוני).
- **גיליון**: [Posts](https://docs.google.com/spreadsheets/d/1Xbor7YEr_apjvmQZ9QYU01UKwKk_EKqlUTH_7C69LIU/edit?gid=128669743#gid=128669743)
- **מצב נוכחי**: פתוח עד שורה 9000 (עודכן: יולי 2026)
- **כשמגיעים לשורה 8500 -- להוסיף עוד 2000 שורות!**
- **סימפטום**: `eligible=0` בלוגים, `MAX(created_at)` ישן

---

## 🚫 קבוצות פייסבוק חסומות

קבוצות שבהן חשבון משה עובדיה חסום ולא ניתן להגיב (פוסטים מסומנים באפור במערכת):

| קבוצה | קישור | גם ב-BLOCKED_GROUPS |
|--------|--------|:---:|
| הובלות, מובילים ממומלצים, חיפוש מובילים | https://www.facebook.com/groups/1629283237109586 | V |
| באר שבע ביחד | https://www.facebook.com/groups/BeerShevaTogether/ | V |
| דלתות פנים במחירי חיסול | https://www.facebook.com/groups/186182019096864 | V |

> עודכן: יוני 2026

---

## 📂 קבצים מרכזיים לתחזוקת Lead Hunter

| קובץ | תפקיד |
|--------|--------|
| `backend/app/tasks/lead_hunter_tasks.py` | תור תגובות, מגבלות יומיות, BLOCKED_GROUPS, שעות פעילות |
| `backend/app/services/lead_hunter_service.py` | פרומפטים AI, סיווג, SKIP_REPLY_KEYWORDS, יצירת תגובות |
| `backend/app/api/facebook_marketing.py` | Extension task pickup + result (pending->working->posted) |
| `backend/app/models/lead_hunter.py` | מודלים: LeadPost, LeadCategory, LeadArea |
| `frontend/app/lead-hunter/page.tsx` | ממשק Lead Hunter + כפתור פרסום |
| `chrome-extension/facebook_reply.js` | פרסום תגובות בפייסבוק (human-like typing) |
| `scripts/lead_hunter_sheets.gs` | Google Apps Script - שולח פוסטים מגיליון לשרת |

### פקודות שרת שימושיות

```bash
# בדיקת לוגים
ssh root@49.13.31.182 "docker logs partnercalc-backend --since 1h 2>&1 | grep lead_hunter | tail -20"

# בדיקת פוסט אחרון
ssh root@49.13.31.182 "docker exec partnercalc-mariadb mysql -u partnercalc -ppartnercalc123 partnercalc -e 'SELECT MAX(created_at) FROM lead_posts;'"

# הפעלת/כיבוי תגובות אוטומטיות
ssh root@49.13.31.182 "docker exec partnercalc-mariadb mysql -u partnercalc -ppartnercalc123 partnercalc -e 'UPDATE lead_categories SET auto_reply_enabled = 1 WHERE id = 1;'"

# ריסטארט backend
ssh root@49.13.31.182 "cd /opt/partnercalc-os && git pull origin main && docker compose -f docker/docker-compose.prod.yml restart backend"

# NOTE: use docker compose (not docker-compose)
```

---

## 📝 License

MIT
