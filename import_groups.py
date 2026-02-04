"""Import Facebook groups from JSON"""
import requests
import json

# הקבוצות שחילצת
groups_data = [
  {"id": "1935697136699450", "name": "משרדים להשכרה - כי גם לך מגיע לעבוד כמו מלך!Last active a year ago", "url": "https://www.facebook.com/groups/1935697136699450"},
  {"id": "1684554685829832", "name": "Vibe Coding - IsraelLast active 3 hours ago", "url": "https://www.facebook.com/groups/1684554685829832"},
  {"id": "715153780127233", "name": "ChatGPT - ישראלLast active 43 minutes ago", "url": "https://www.facebook.com/groups/715153780127233"},
  {"id": "595871357221372", "name": "תושבי להביםLast active 45 minutes ago", "url": "https://www.facebook.com/groups/595871357221372"},
  {"id": "369537586455596", "name": "דירות להשכרה ולמכירה בראשון לציוןLast active 52 minutes ago", "url": "https://www.facebook.com/groups/369537586455596"},
  {"id": "1472569969685762", "name": "דירות בשושו ראשון לציון נס ציונה רחובות - אין כניסה למתווכיםLast active 2 hours ago", "url": "https://www.facebook.com/groups/1472569969685762"},
  {"id": "1652449762253121", "name": "WWF Attitude EraLast active about an hour ago", "url": "https://www.facebook.com/groups/1652449762253121"},
  {"id": "16509128653", "name": "איך אתה יודע שאתה רחובותיLast active about an hour ago", "url": "https://www.facebook.com/groups/16509128653"},
  {"id": "731670323675108", "name": "אבא פגום - שורדים ביחדLast active 2 hours ago", "url": "https://www.facebook.com/groups/731670323675108"},
  {"id": "441015746083854", "name": "למסירה - הכל בחינםLast active 39 minutes ago", "url": "https://www.facebook.com/groups/441015746083854"},
  {"id": "342475045797387", "name": "שאל עורך דין!Last active 2 hours ago", "url": "https://www.facebook.com/groups/342475045797387"},
  {"id": "1877655269059208", "name": "טסלה ישראל - כאן הכל קורה !Last active 5 minutes ago", "url": "https://www.facebook.com/groups/1877655269059208"},
  {"id": "288666474617177", "name": "מטיילים עם ילדיםLast active 39 minutes ago", "url": "https://www.facebook.com/groups/288666474617177"},
  {"id": "1523672414666153", "name": "הפורום החשמלאי הארציLast active 42 minutes ago", "url": "https://www.facebook.com/groups/1523672414666153"},
  {"id": "676168705860078", "name": "עשיתי לבד- עבודות יד עשה/י זאת בעצמךLast active 58 minutes ago", "url": "https://www.facebook.com/groups/676168705860078"},
  {"id": "613923128999186", "name": "תאילנד למשפחות- החופשה המושלמת❤Last active 37 minutes ago", "url": "https://www.facebook.com/groups/613923128999186"},
  {"id": "514475351900297", "name": "בחורות ובחורים שווים בין חבריםLast active about an hour ago", "url": "https://www.facebook.com/groups/514475351900297"},
  {"id": "1307217126002988", "name": "מודליסטיות ועסקים |  freelance modelsLast active 2 minutes ago", "url": "https://www.facebook.com/groups/1307217126002988"},
  {"id": "1364459958209699", "name": "N8n automation B2BLast active 2 hours ago", "url": "https://www.facebook.com/groups/1364459958209699"},
  {"id": "729798648321198", "name": "Midjourney ai Israel - מידג'רני ישראלLast active 4 hours ago", "url": "https://www.facebook.com/groups/729798648321198"},
  {"id": "684971004945350", "name": "חיים בסרט - קהילת חובבי קולנועLast active 22 minutes ago", "url": "https://www.facebook.com/groups/684971004945350"},
  {"id": "683559832871896", "name": "וידויים של נשואים 🤫Last active 2 days ago", "url": "https://www.facebook.com/groups/683559832871896"},
  {"id": "995459269452472", "name": "Google Veo 3Last active 19 hours ago", "url": "https://www.facebook.com/groups/995459269452472"},
  {"id": "111216171140889", "name": "Keto Z JajemLast active 3 hours ago", "url": "https://www.facebook.com/groups/111216171140889"},
  {"id": "1751139384947726", "name": "טסלה ישראל - Tesla IsraelLast active 22 minutes ago", "url": "https://www.facebook.com/groups/1751139384947726"},
  {"id": "882018605193426", "name": "עומר מיתר להבים - יישובי הלוויןLast active 2 minutes ago", "url": "https://www.facebook.com/groups/882018605193426"},
  {"id": "300956149628118", "name": "Tesla 2025+ Model Y Juniper Owners ClubLast active 3 hours ago", "url": "https://www.facebook.com/groups/300956149628118"},
  {"id": "1630973707171094", "name": "בריכות שחייה בישראל  Swimming Pools In IsraelLast active about an hour ago", "url": "https://www.facebook.com/groups/1630973707171094"},
  {"id": "200529521199903", "name": "תזונה קטוגנית למתחילים - הקבוצה הרשמיתLast active 2 hours ago", "url": "https://www.facebook.com/groups/200529521199903"},
  {"id": "1570826313211240", "name": "שאל חשמלאיLast active about an hour ago", "url": "https://www.facebook.com/groups/1570826313211240"},
  {"id": "352378592677223", "name": "מחתרת הבשרLast active 21 hours ago", "url": "https://www.facebook.com/groups/352378592677223"},
  {"id": "104842322913689", "name": "פשפשוק - חשמל ואלקטרוניקהLast active 17 minutes ago", "url": "https://www.facebook.com/groups/104842322913689"},
  {"id": "253753689848149", "name": "❗❗כלבים למסירה בלבדLast active 22 minutes ago", "url": "https://www.facebook.com/groups/253753689848149"},
  {"id": "190021685310836", "name": "אוהבי הכלבים- אימוץ בלבד!!Last active 8 minutes ago", "url": "https://www.facebook.com/groups/190021685310836"},
  {"id": "205363539479412", "name": "פאפאזוןLast active 13 hours ago", "url": "https://www.facebook.com/groups/205363539479412"},
  {"id": "1244175850623484", "name": "N8N TemplatesLast active 6 hours ago", "url": "https://www.facebook.com/groups/1244175850623484"},
  {"id": "822939235350571", "name": "עבודות ריצוףLast active about an hour ago", "url": "https://www.facebook.com/groups/822939235350571"},
  {"id": "521150684994764", "name": "תושבי להבים - קבוצה רישמיתLast active 5 minutes ago", "url": "https://www.facebook.com/groups/521150684994764"},
  {"id": "957311694362184", "name": "פשפשוק - עסקיםLast active 21 hours ago", "url": "https://www.facebook.com/groups/957311694362184"},
  {"id": "1920854911477422", "name": "דרושים מתכנתים ואנשי פיתוחLast active 20 minutes ago", "url": "https://www.facebook.com/groups/1920854911477422"},
  {"id": "357382001599509", "name": "קיטו ישראל- דיאטה קטוגנית כאורח חיים בריאLast active a day ago", "url": "https://www.facebook.com/groups/357382001599509"},
  {"id": "395463213831721", "name": "הצעות עבודה / דרושים / מחפשים עבודה - מוצאים מפה לאוזןLast active about a minute ago", "url": "https://www.facebook.com/groups/395463213831721"},
  {"id": "527532664012197", "name": "קהילת הכדורסלLast active 11 minutes ago", "url": "https://www.facebook.com/groups/527532664012197"},
  {"id": "255468097927099", "name": "לוח זולוLast active about an hour ago", "url": "https://www.facebook.com/groups/255468097927099"},
  {"id": "1182350255946784", "name": "רכב חשמלי / עמדת טעינה - מידע והתייעצותLast active 19 hours ago", "url": "https://www.facebook.com/groups/1182350255946784"},
  {"id": "168042543290308", "name": "פרסום ממומן PPC |  קידום אתרים  SEO | שיווק דיגיטלי ומה שבינהם🙂Last active 36 minutes ago", "url": "https://www.facebook.com/groups/168042543290308"},
  {"id": "1493025154254115", "name": "תזונה קטוגניתLast active 17 hours ago", "url": "https://www.facebook.com/groups/1493025154254115"},
  {"id": "1790393431742800", "name": "מדברים בינה: הבית של חובבי ה-AILast active 2 hours ago", "url": "https://www.facebook.com/groups/1790393431742800"},
  {"id": "743300832520453", "name": "דירות למכירה ברחובותLast active 21 minutes ago", "url": "https://www.facebook.com/groups/743300832520453"},
  {"id": "1953095061645246", "name": "זכרונות ילדות-בת יםLast active 3 days ago", "url": "https://www.facebook.com/groups/1953095061645246"},
]

# שלח לשרת
API_URL = "https://partners.ppcmedia.co.il/api/facebook/groups/bulk-import"

try:
    response = requests.post(
        API_URL,
        json={"groups": groups_data},
        verify=False,  # Skip SSL verification for self-signed cert
        timeout=60
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
