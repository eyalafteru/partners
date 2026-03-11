/**
 * Lead Hunter - Google Apps Script
 * ===================================
 * מושך פוסטים חדשים מגיליון "all_posts" ושולח לשרת PartnerCalc
 *
 * הגדרה:
 * 1. פתח את הגיליון ב-Google Sheets
 * 2. Extensions → Apps Script → הדבק את הקוד הזה
 * 3. עדכן את BACKEND_URL ו-INGEST_TOKEN
 * 4. הרץ פעם אחת: setupTrigger()
 * 5. ה-script ירוץ אוטומטית כל 5 דקות
 *
 * מבנה הגיליון:
 * A: url | B: description | C: posted_at | D: group_name | E: group_url | F: actor_name | G: actor_url | H: sent
 */

// ============================================================
//  הגדרות - שנה לפי הצורך
// ============================================================

const BACKEND_URL = "https://partners.ppcmedia.co.il/api/lead-hunter/ingest";
const INGEST_TOKEN = "lead-hunter-secret-2024";
const SHEET_NAME = "users_userpost";
const SENT_COLUMN = 8;       // עמודה H
const START_ROW = 40;        // מתחיל מ-40
const BATCH_SIZE = 20;       // כמה שורות לשלוח בכל ריצה


// ============================================================
//  פונקציה ראשית - רצה כל 5 דקות
// ============================================================

function syncNewPosts() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME);

  if (!sheet) {
    Logger.log("❌ Sheet '" + SHEET_NAME + "' not found");
    return;
  }

  const lastRow = sheet.getLastRow();
  if (lastRow < START_ROW) {
    Logger.log("📭 No data rows found");
    return;
  }

  let sent = 0;
  let skipped = 0;
  let errors = 0;

  for (let row = START_ROW; row <= lastRow; row++) {
    // בדיקה האם כבר נשלח
    const sentCell = sheet.getRange(row, SENT_COLUMN).getValue();
    if (sentCell === true || sentCell === "TRUE" || sentCell === "sent") {
      skipped++;
      continue;
    }

    // קריאת הנתונים
    const url         = sheet.getRange(row, 1).getValue();
    const description = sheet.getRange(row, 2).getValue();
    const postedAt    = sheet.getRange(row, 3).getValue();
    const groupName   = sheet.getRange(row, 4).getValue();
    const groupUrl    = sheet.getRange(row, 5).getValue();
    const actorName   = sheet.getRange(row, 6).getValue() || sheet.getRange(row, 7).getValue(); // F או G
    const actorUrl    = sheet.getRange(row, 7).getValue();

    // ולידציה בסיסית
    if (!url || !description) {
      Logger.log("⚠️ Row " + row + ": missing url or description - skipping");
      skipped++;
      continue;
    }

    // פרמוט תאריך
    let postedAtStr = "";
    if (postedAt) {
      try {
        const d = new Date(postedAt);
        postedAtStr = d.toISOString();
      } catch (e) {
        postedAtStr = String(postedAt);
      }
    }

    // שליחה לשרת
    const payload = {
      url: String(url).trim(),
      description: String(description).trim(),
      posted_at: postedAtStr,
      group_name: String(groupName || "").trim(),
      group_url: String(groupUrl || "").trim(),
      actor_name: String(actorName || "").trim(),
      actor_url: String(actorUrl || "").trim(),
    };

    try {
      const response = UrlFetchApp.fetch(BACKEND_URL, {
        method: "post",
        contentType: "application/json",
        headers: {
          "X-Ingest-Token": INGEST_TOKEN,
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
        followRedirects: true,
      });

      const code = response.getResponseCode();

      if (code === 200) {
        const result = JSON.parse(response.getContentText());
        // סמן כנשלח גם אם כפול (כדי לא לשלוח שוב)
        sheet.getRange(row, SENT_COLUMN).setValue("sent");
        sent++;
        Logger.log("✅ Row " + row + ": " + result.status + " | url=" + String(url).substring(0, 60));
      } else {
        Logger.log("❌ Row " + row + ": HTTP " + code + " | " + response.getContentText().substring(0, 200));
        errors++;
      }

    } catch (e) {
      Logger.log("❌ Row " + row + " exception: " + e.toString());
      errors++;
    }

    // הגבלת batch - אל תשלח יותר מדי בריצה אחת
    if (sent >= BATCH_SIZE) {
      Logger.log("📦 Batch limit reached (" + BATCH_SIZE + ") - will continue next run");
      break;
    }

    // השהייה קטנה בין קריאות (למניעת rate limit)
    if (sent % 5 === 0) {
      Utilities.sleep(500);
    }
  }

  Logger.log("📊 Done: sent=" + sent + " | skipped=" + skipped + " | errors=" + errors);
}


// ============================================================
//  הגדרת Trigger אוטומטי (הרץ פעם אחת!)
// ============================================================

function setupTrigger() {
  // מחק טריגרים קיימים
  const triggers = ScriptApp.getProjectTriggers();
  for (const t of triggers) {
    if (t.getHandlerFunction() === "syncNewPosts") {
      ScriptApp.deleteTrigger(t);
    }
  }

  // צור טריגר חדש - כל 5 דקות
  ScriptApp.newTrigger("syncNewPosts")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log("✅ Trigger created - syncNewPosts will run every 5 minutes");
}


// ============================================================
//  ריצה ידנית חד-פעמית לבדיקה
// ============================================================

function testSendOne() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME);

  // שלח את השורה השנייה (הראשונה עם נתונים) ללא סימון "נשלח"
  const row = 2;
  const url         = sheet.getRange(row, 1).getValue();
  const description = sheet.getRange(row, 2).getValue();
  const postedAt    = sheet.getRange(row, 3).getValue();
  const groupName   = sheet.getRange(row, 4).getValue();
  const groupUrl    = sheet.getRange(row, 5).getValue();
  const actorName   = sheet.getRange(row, 6).getValue();
  const actorUrl    = sheet.getRange(row, 7).getValue();

  const payload = {
    url: String(url).trim(),
    description: String(description).trim(),
    posted_at: postedAt ? new Date(postedAt).toISOString() : "",
    group_name: String(groupName || "").trim(),
    group_url: String(groupUrl || "").trim(),
    actor_name: String(actorName || "").trim(),
    actor_url: String(actorUrl || "").trim(),
  };

  Logger.log("📤 Test payload: " + JSON.stringify(payload).substring(0, 300));

  const response = UrlFetchApp.fetch(BACKEND_URL, {
    method: "post",
    contentType: "application/json",
    headers: { "X-Ingest-Token": INGEST_TOKEN },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });

  Logger.log("📥 Response " + response.getResponseCode() + ": " + response.getContentText());
}
