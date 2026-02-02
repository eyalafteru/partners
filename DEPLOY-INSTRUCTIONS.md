# הוראות התקנה - PartnerCalc OS

## שלב 1: העלאת הפרויקט לשרת

### אפשרות A - עם Git (מומלץ)

1. צור repository חדש ב-GitHub
2. במחשב המקומי, הרץ:
```powershell
cd "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/partnercalc-os.git
git push -u origin main
```

3. בשרת, הרץ:
```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/partnercalc-os.git
```

### אפשרות B - העלאה ישירה עם SCP

מהמחשב המקומי:
```powershell
scp -r "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os" root@49.13.31.182:/opt/
```

---

## שלב 2: התחברות לשרת

```bash
ssh root@49.13.31.182
# סיסמה: PtU9xMCXjhnKRKVMkCEm!
```

---

## שלב 3: התקנת Docker (בשרת)

```bash
# עדכון מערכת
apt update && apt upgrade -y

# התקנת Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# וידוא התקנה
docker --version
docker compose version
```

---

## שלב 4: הגדרת SSL ו-Hosts (בשרת)

```bash
# הוספת דומיין ל-hosts
echo "127.0.0.1 partners.ppcmedia.co.il" >> /etc/hosts

# יצירת SSL certificate
mkdir -p /etc/ssl/private
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt \
    -subj "/CN=partners.ppcmedia.co.il"
```

---

## שלב 5: הגדרת Environment (בשרת)

```bash
cd /opt/partnercalc-os/backend

# יצירת קובץ .env
cp env.example.txt .env

# עריכת הקובץ עם ה-API keys שלך
nano .env
```

**חשוב! עדכן את הערכים הבאים ב-.env:**
- `OPENAI_API_KEY=sk-...` (חובה!)
- `APIFY_TOKEN=...` (חובה!)
- `SMTP_PASSWORD=...` (לשליחת מיילים)
- `IMAP_PASSWORD=...` (לקריאת מיילים)

---

## שלב 6: הפעלת Docker (בשרת)

```bash
cd /opt/partnercalc-os/docker

# בנייה והפעלה
docker compose -f docker-compose.prod.yml up -d --build

# בדיקת סטטוס
docker compose -f docker-compose.prod.yml ps

# צפייה בלוגים
docker compose -f docker-compose.prod.yml logs -f
```

---

## שלב 7: העברת Database (בשרת)

### העלאת קובץ ה-DB מהמחשב המקומי:
```powershell
scp "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\backend\partnercalc.db" root@49.13.31.182:/opt/partnercalc-os/backend/
```

### הרצת מיגרציה בשרת:
```bash
cd /opt/partnercalc-os/backend

# התקנת Python dependencies
apt install -y python3 python3-pip
pip3 install pymysql

# הרצת מיגרציה
python3 migrate_sqlite_to_mariadb.py
```

---

## שלב 8: הגדרת Hosts במחשב המקומי (לבדיקה)

### Windows:
פתח כמנהל: `C:\Windows\System32\drivers\etc\hosts`

הוסף שורה:
```
49.13.31.182 partners.ppcmedia.co.il
```

---

## שלב 9: בדיקה

פתח בדפדפן:
```
https://partners.ppcmedia.co.il
```

(יופיע אזהרת SSL כי זה self-signed - לחץ "Advanced" ו-"Proceed")

---

## פקודות שימושיות

```bash
# צפייה בלוגים
docker compose -f docker-compose.prod.yml logs -f

# הפעלה מחדש
docker compose -f docker-compose.prod.yml restart

# עצירה
docker compose -f docker-compose.prod.yml down

# בנייה מחדש
docker compose -f docker-compose.prod.yml up -d --build
```

---

## פתרון בעיות

### אם הממשק לא עולה:
```bash
# בדוק שכל הcontainers רצים
docker compose -f docker-compose.prod.yml ps

# בדוק לוגים
docker compose -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.prod.yml logs frontend
docker compose -f docker-compose.prod.yml logs backend
```

### אם MariaDB לא עולה:
```bash
# מחק volumes והתחל מחדש
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```
