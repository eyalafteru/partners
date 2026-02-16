/**
 * PartnerCalc Cookie Sync - Popup Script
 */

const statusDot = document.getElementById("statusDot");
const statusLabel = document.getElementById("statusLabel");
const statusDetail = document.getElementById("statusDetail");
const lastSync = document.getElementById("lastSync");
const cookieCount = document.getElementById("cookieCount");
const syncBtn = document.getElementById("syncBtn");
const openFbBtn = document.getElementById("openFbBtn");
const autoSyncToggle = document.getElementById("autoSyncToggle");
const backendUrlInput = document.getElementById("backendUrl");
const messageEl = document.getElementById("message");

// ========== Load Status ==========

async function loadStatus() {
  try {
    const status = await chrome.runtime.sendMessage({ action: "getStatus" });

    // Update status indicator
    if (status.isLoggedIn) {
      statusDot.className = "status-dot green";
      statusLabel.textContent = "מחובר לפייסבוק";
      statusDetail.textContent = `${status.cookieCount} cookies`;
      openFbBtn.style.display = "none";
    } else {
      statusDot.className = "status-dot red";
      statusLabel.textContent = "לא מחובר לפייסבוק";
      statusDetail.textContent = "יש להתחבר כדי לסנכרן";
      openFbBtn.style.display = "block";
    }

    // Sync status
    if (status.lastSyncTime) {
      const date = new Date(status.lastSyncTime);
      const timeStr = date.toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit" });
      const dateStr = date.toLocaleDateString("he-IL");
      lastSync.textContent = `${dateStr} ${timeStr}`;

      if (status.lastSyncStatus === "success") {
        lastSync.style.color = "#1e7e34";
      } else if (status.lastSyncStatus === "error") {
        lastSync.style.color = "#c62828";
      }
    } else {
      lastSync.textContent = "לא סונכרן עדיין";
      lastSync.style.color = "#65676b";
    }

    cookieCount.textContent = status.cookieCount || "0";

    // Settings
    autoSyncToggle.checked = status.autoSync;
    backendUrlInput.value = status.backendUrl;

    // Enable sync button
    syncBtn.disabled = false;
  } catch (err) {
    statusDot.className = "status-dot gray";
    statusLabel.textContent = "שגיאה";
    statusDetail.textContent = err.message;
  }
}

// ========== Sync Button ==========

syncBtn.addEventListener("click", async () => {
  syncBtn.disabled = true;
  syncBtn.innerHTML = '🔄 מסנכרן...<span class="spinner"></span>';
  hideMessage();

  try {
    const result = await chrome.runtime.sendMessage({ action: "syncNow" });

    if (result.success) {
      if (result.reason === "unchanged") {
        showMessage("success", "ה-Cookies כבר מעודכנים - אין שינוי");
      } else {
        showMessage("success", "Cookies סונכרנו בהצלחה!");
      }
    } else {
      if (result.reason === "not_logged_in") {
        showMessage("error", "לא מחובר לפייסבוק - יש להתחבר קודם");
      } else {
        showMessage("error", `שגיאה: ${result.error || "לא ידועה"}`);
      }
    }
  } catch (err) {
    showMessage("error", `שגיאה: ${err.message}`);
  }

  syncBtn.innerHTML = "🔄 סנכרן עכשיו";
  syncBtn.disabled = false;

  // Refresh status
  await loadStatus();
});

// ========== Open Facebook ==========

openFbBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ action: "openFacebook" });
  showMessage("success", "פייסבוק נפתח - התחבר ולחץ סנכרן");
});

// ========== Auto Sync Toggle ==========

autoSyncToggle.addEventListener("change", async () => {
  await chrome.runtime.sendMessage({
    action: "setAutoSync",
    enabled: autoSyncToggle.checked
  });
});

// ========== Backend URL ==========

let backendUrlTimeout = null;
backendUrlInput.addEventListener("input", () => {
  if (backendUrlTimeout) clearTimeout(backendUrlTimeout);
  backendUrlTimeout = setTimeout(async () => {
    const url = backendUrlInput.value.replace(/\/+$/, ""); // Remove trailing slashes
    await chrome.runtime.sendMessage({ action: "setBackendUrl", url });
    showMessage("success", "Backend URL עודכן");
  }, 800);
});

// ========== Message Display ==========

function showMessage(type, text) {
  messageEl.className = `message ${type}`;
  messageEl.textContent = text;
  messageEl.style.display = "block";
}

function hideMessage() {
  messageEl.style.display = "none";
}

// ========== Init ==========

loadStatus();
