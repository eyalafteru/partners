/**
 * PartnerCalc Cookie Sync - Background Service Worker
 * 
 * Listens for Facebook cookie changes and auto-syncs to the backend.
 * Uses chrome.cookies.onChanged for reactive sync and chrome.alarms for periodic backup sync.
 */

const DEFAULT_BACKEND_URL = "http://localhost:8001";
const ESSENTIAL_COOKIES = ["c_user", "xs", "fr"];
const DEBOUNCE_MS = 2000;
const PERIODIC_SYNC_MINUTES = 30;

let debounceTimer = null;
let lastSentHash = "";

// ========== Cookie Extraction ==========

async function extractFacebookCookies() {
  try {
    const cookies = await chrome.cookies.getAll({ domain: ".facebook.com" });

    // Filter out empty cookies and convert to Apify/Playwright format
    const formatted = cookies
      .filter(c => c.name && c.value)
      .map(c => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path,
        expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
        httpOnly: c.httpOnly,
        secure: c.secure,
        sameSite: mapSameSite(c.sameSite)
      }));

    const cookieNames = new Set(formatted.map(c => c.name));
    const hasEssential = ESSENTIAL_COOKIES.every(name => cookieNames.has(name));

    return {
      cookies: formatted,
      isLoggedIn: hasEssential,
      hasEssential,
      cookieCount: formatted.length,
      essentialStatus: ESSENTIAL_COOKIES.map(name => ({
        name,
        present: cookieNames.has(name)
      }))
    };
  } catch (err) {
    console.error("[PartnerCalc] Failed to extract cookies:", err);
    return { cookies: [], isLoggedIn: false, hasEssential: false, cookieCount: 0, essentialStatus: [] };
  }
}

/**
 * Map Chrome's sameSite values to Playwright/Apify expected values.
 * Chrome returns: "unspecified", "no_restriction", "lax", "strict"
 * Playwright expects: "Strict", "Lax", "None"
 */
function mapSameSite(chromeSameSite) {
  switch (chromeSameSite) {
    case "strict":        return "Strict";
    case "lax":           return "Lax";
    case "no_restriction": return "None";
    case "unspecified":   return "Lax";
    default:              return "Lax";
  }
}

// ========== Hash for Change Detection ==========

function computeCookieHash(cookies) {
  // Hash based on essential cookie values only
  const essentialValues = ESSENTIAL_COOKIES
    .map(name => {
      const cookie = cookies.find(c => c.name === name);
      return cookie ? `${name}=${cookie.value}` : "";
    })
    .join("|");
  
  // Simple string hash
  let hash = 0;
  for (let i = 0; i < essentialValues.length; i++) {
    const chr = essentialValues.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0;
  }
  return hash.toString();
}

// ========== Backend Communication ==========

async function getBackendUrl() {
  const result = await chrome.storage.local.get(["backendUrl"]);
  return result.backendUrl || DEFAULT_BACKEND_URL;
}

async function sendToBackend(cookies) {
  const backendUrl = await getBackendUrl();
  const url = `${backendUrl}/api/facebook/cookies/upload`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies })
    });

    if (response.ok) {
      const data = await response.json();
      const now = new Date().toISOString();
      await chrome.storage.local.set({
        lastSyncTime: now,
        lastSyncStatus: "success",
        lastSyncMessage: data.message || "Synced successfully",
        lastCookieCount: cookies.length
      });
      console.log(`[PartnerCalc] Cookies synced: ${cookies.length} cookies`);
      return { success: true, data };
    } else {
      const errData = await response.json().catch(() => ({ detail: response.statusText }));
      await chrome.storage.local.set({
        lastSyncStatus: "error",
        lastSyncMessage: errData.detail || `HTTP ${response.status}`
      });
      console.error(`[PartnerCalc] Sync failed: ${response.status}`, errData);
      return { success: false, error: errData.detail };
    }
  } catch (err) {
    await chrome.storage.local.set({
      lastSyncStatus: "error",
      lastSyncMessage: `Backend not reachable: ${err.message}`
    });
    console.error("[PartnerCalc] Backend not reachable:", err.message);
    return { success: false, error: err.message };
  }
}

// ========== Sync Logic ==========

async function syncCookies(force = false) {
  const { cookies, isLoggedIn, hasEssential } = await extractFacebookCookies();

  if (!hasEssential) {
    await chrome.storage.local.set({
      lastSyncStatus: "logged_out",
      lastSyncMessage: "Not logged in to Facebook",
      isLoggedIn: false
    });
    console.log("[PartnerCalc] Not logged in to Facebook - skipping sync");
    return { success: false, reason: "not_logged_in" };
  }

  // Check if cookies changed (skip if same as last sent)
  const currentHash = computeCookieHash(cookies);
  if (!force && currentHash === lastSentHash) {
    console.log("[PartnerCalc] Cookies unchanged - skipping sync");
    return { success: true, reason: "unchanged" };
  }

  // Send to backend
  const result = await sendToBackend(cookies);

  if (result.success) {
    lastSentHash = currentHash;
    await chrome.storage.local.set({ isLoggedIn: true });
  }

  return result;
}

// ========== Reactive Sync: cookie onChange ==========

chrome.cookies.onChanged.addListener((changeInfo) => {
  // Only react to facebook.com cookies
  const domain = changeInfo.cookie.domain;
  if (!domain.includes("facebook.com")) return;

  // Debounce - login changes many cookies in rapid succession
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(async () => {
    debounceTimer = null;

    const settings = await chrome.storage.local.get(["autoSync"]);
    if (settings.autoSync === false) return; // Auto-sync disabled

    console.log(`[PartnerCalc] Facebook cookie changed: ${changeInfo.cookie.name} (${changeInfo.cause})`);
    await syncCookies();
  }, DEBOUNCE_MS);
});

// ========== Periodic Sync via Alarms ==========

chrome.alarms.create("periodicSync", { periodInMinutes: PERIODIC_SYNC_MINUTES });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "periodicSync") {
    const settings = await chrome.storage.local.get(["autoSync"]);
    if (settings.autoSync === false) return;

    console.log("[PartnerCalc] Periodic sync triggered");
    await syncCookies();
  }
});

// ========== Message Handling (from popup AND content bridge) ==========

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "syncNow") {
    syncCookies(true).then(sendResponse);
    return true; // keep channel open for async response
  }

  // Used by the content bridge: extract fresh cookies, sync to backend, return result
  if (message.action === "syncAndReturn") {
    (async () => {
      const { cookies, isLoggedIn, hasEssential, cookieCount } = await extractFacebookCookies();
      
      if (!hasEssential) {
        sendResponse({
          synced: false,
          isLoggedIn: false,
          reason: "not_logged_in",
          message: "לא מחובר לפייסבוק - יש להתחבר קודם"
        });
        return;
      }

      // Force-sync fresh cookies to backend
      const result = await sendToBackend(cookies);
      
      if (result.success) {
        lastSentHash = computeCookieHash(cookies);
        await chrome.storage.local.set({ isLoggedIn: true });
      }

      sendResponse({
        synced: result.success,
        isLoggedIn: true,
        cookieCount,
        message: result.success 
          ? `סונכרנו ${cookieCount} cookies בהצלחה` 
          : `שגיאה בסנכרון: ${result.error}`
      });
    })();
    return true; // async response
  }

  if (message.action === "getStatus") {
    extractFacebookCookies().then(async (result) => {
      const stored = await chrome.storage.local.get([
        "lastSyncTime", "lastSyncStatus", "lastSyncMessage",
        "autoSync", "backendUrl", "isLoggedIn"
      ]);
      sendResponse({
        ...result,
        lastSyncTime: stored.lastSyncTime || null,
        lastSyncStatus: stored.lastSyncStatus || "never",
        lastSyncMessage: stored.lastSyncMessage || "Never synced",
        autoSync: stored.autoSync !== false, // default true
        backendUrl: stored.backendUrl || DEFAULT_BACKEND_URL
      });
    });
    return true;
  }

  if (message.action === "setAutoSync") {
    chrome.storage.local.set({ autoSync: message.enabled });
    sendResponse({ ok: true });
    return false;
  }

  if (message.action === "setBackendUrl") {
    chrome.storage.local.set({ backendUrl: message.url });
    sendResponse({ ok: true });
    return false;
  }

  if (message.action === "openFacebook") {
    chrome.tabs.create({ url: "https://www.facebook.com/" });
    sendResponse({ ok: true });
    return false;
  }
});

// ========== Initial Sync on Install/Startup ==========

chrome.runtime.onInstalled.addListener(async () => {
  console.log("[PartnerCalc] Extension installed - running initial sync");
  await chrome.storage.local.set({ autoSync: true });
  await syncCookies(true);
});

chrome.runtime.onStartup.addListener(async () => {
  console.log("[PartnerCalc] Browser started - running sync");
  await syncCookies();
});
