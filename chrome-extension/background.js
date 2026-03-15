/**
 * PartnerCalc Cookie Sync + Reply Worker - Background Service Worker
 * 
 * 1) Cookie sync: reactive (onChanged) + periodic (alarm)
 * 2) Reply tasks: polls backend for pending_extension tasks and dispatches
 *    them to a Facebook tab running facebook_reply.js content script.
 */

const DEFAULT_BACKEND_URL = "http://localhost:8000";
const ESSENTIAL_COOKIES = ["c_user", "xs", "fr"];
const DEBOUNCE_MS = 2000;
const PERIODIC_SYNC_MINUTES = 30;
const TASK_POLL_SECONDS = 45;

let debounceTimer = null;
let lastSentHash = "";
let taskBusy = false;

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
chrome.alarms.create("taskPoll", { periodInMinutes: TASK_POLL_SECONDS / 60 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "periodicSync") {
    const settings = await chrome.storage.local.get(["autoSync"]);
    if (settings.autoSync === false) return;

    console.log("[PartnerCalc] Periodic sync triggered");
    await syncCookies();
  }

  if (alarm.name === "taskPoll") {
    const settings = await chrome.storage.local.get(["replyEnabled"]);
    if (settings.replyEnabled === false) return;
    await pollForTasks();
  }
});

// ========== Reply Task Polling ==========

async function sendBackendLog(level, message, replyId) {
  try {
    const backendUrl = await getBackendUrl();
    const params = new URLSearchParams({ level, message });
    if (replyId) params.set("reply_id", replyId);
    await fetch(`${backendUrl}/api/facebook/extension/log?${params}`);
  } catch (_) { /* best-effort */ }
}

async function pollForTasks() {
  if (taskBusy) {
    console.log("[PartnerCalc] Task poll skipped - already working on a task");
    return;
  }

  const backendUrl = await getBackendUrl();
  let taskData;

  try {
    const resp = await fetch(`${backendUrl}/api/facebook/extension/pending-tasks`);
    if (!resp.ok) return;
    taskData = await resp.json();
  } catch (err) {
    console.log("[PartnerCalc] Task poll failed:", err.message);
    return;
  }

  if (!taskData.has_task) return;

  const task = taskData.task;
  const taskType = task.task_type || "marketing";
  const taskId = task.reply_id || task.lead_post_id;
  console.log(`[PartnerCalc] 📋 Got ${taskType} task: id=${taskId} post=${task.post_url}`);
  await sendBackendLog("info", `Picked up ${taskType} task id=${taskId}`, task.reply_id);

  taskBusy = true;
  await chrome.storage.local.set({
    currentTask: task,
    currentTaskStatus: "working",
    currentTaskTime: new Date().toISOString(),
  });

  try {
    const result = await executeTaskInTab(task);

    const resultBody = {
      task_type: taskType,
      success: result.success,
      error: result.error || null,
    };
    if (task.reply_id) resultBody.reply_id = task.reply_id;
    if (task.lead_post_id) resultBody.lead_post_id = task.lead_post_id;

    await fetch(`${backendUrl}/api/facebook/extension/task-result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(resultBody),
    });

    const status = result.success ? "✅ success" : `❌ failed: ${result.error}`;
    console.log(`[PartnerCalc] Task result (${taskType}): ${status}`);
    await sendBackendLog(result.success ? "info" : "error", `Task result: ${status}`, task.reply_id);

    await chrome.storage.local.set({
      currentTask: null,
      currentTaskStatus: result.success ? "last_success" : "last_failed",
      lastTaskResult: { ...result, task_type: taskType, reply_id: task.reply_id, lead_post_id: task.lead_post_id, time: new Date().toISOString() },
    });
  } catch (err) {
    console.error("[PartnerCalc] Task execution error:", err);
    await sendBackendLog("error", `Task crashed: ${err.message}`, task.reply_id);

    try {
      const errorBody = {
        task_type: taskType,
        success: false,
        error: `Extension error: ${err.message}`,
      };
      if (task.reply_id) errorBody.reply_id = task.reply_id;
      if (task.lead_post_id) errorBody.lead_post_id = task.lead_post_id;

      await fetch(`${backendUrl}/api/facebook/extension/task-result`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(errorBody),
      });
    } catch (_) { /* best-effort */ }

    await chrome.storage.local.set({
      currentTask: null,
      currentTaskStatus: "last_failed",
      lastTaskResult: { success: false, error: err.message, task_type: taskType, reply_id: task.reply_id, lead_post_id: task.lead_post_id, time: new Date().toISOString() },
    });
  } finally {
    taskBusy = false;
  }
}

async function executeTaskInTab(task) {
  const postUrl = task.post_url;
  await sendBackendLog("info", `Opening tab: ${postUrl}`, task.reply_id);

  // Open Facebook post in a new tab
  const tab = await chrome.tabs.create({ url: postUrl, active: false });

  // Wait for tab to finish loading
  await new Promise((resolve) => {
    function onUpdate(tabId, info) {
      if (tabId === tab.id && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(onUpdate);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(onUpdate);
    // Safety timeout
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(onUpdate);
      resolve();
    }, 30000);
  });

  await sendBackendLog("info", "Tab loaded, sending executeReply message", task.reply_id);

  // Send task to the content script
  let result;
  try {
    result = await chrome.tabs.sendMessage(tab.id, {
      action: "executeReply",
      task,
    });
  } catch (err) {
    await sendBackendLog("error", `sendMessage failed: ${err.message}`, task.reply_id);
    result = { success: false, error: `Content script not responding: ${err.message}` };
  }

  // Close tab after a short delay (keep it briefly for debugging)
  setTimeout(() => {
    chrome.tabs.remove(tab.id).catch(() => {});
  }, 5000);

  return result || { success: false, error: "No response from content script" };
}

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
        "autoSync", "backendUrl", "isLoggedIn",
        "replyEnabled", "currentTask", "currentTaskStatus", "lastTaskResult",
      ]);
      sendResponse({
        ...result,
        lastSyncTime: stored.lastSyncTime || null,
        lastSyncStatus: stored.lastSyncStatus || "never",
        lastSyncMessage: stored.lastSyncMessage || "Never synced",
        autoSync: stored.autoSync !== false,
        backendUrl: stored.backendUrl || DEFAULT_BACKEND_URL,
        replyEnabled: stored.replyEnabled !== false,
        currentTask: stored.currentTask || null,
        currentTaskStatus: stored.currentTaskStatus || "idle",
        lastTaskResult: stored.lastTaskResult || null,
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

  if (message.action === "setReplyEnabled") {
    chrome.storage.local.set({ replyEnabled: message.enabled });
    console.log(`[PartnerCalc] Reply tasks ${message.enabled ? "enabled" : "disabled"}`);
    sendResponse({ ok: true });
    return false;
  }

  if (message.action === "pollNow") {
    pollForTasks().then(() => sendResponse({ ok: true }));
    return true;
  }

  // Log forwarding from content script → backend
  if (message.action === "extensionLog") {
    sendBackendLog(message.level, message.message, message.replyId);
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
