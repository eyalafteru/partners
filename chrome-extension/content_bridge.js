/**
 * PartnerCalc Cookie Sync - Content Bridge
 * 
 * This content script bridges between the PartnerCalc frontend page
 * and the Chrome extension's background service worker.
 * 
 * Flow:
 *   Frontend (window.postMessage) → Content Script → (chrome.runtime.sendMessage) → Background.js
 *   Background.js → (sendResponse) → Content Script → (window.postMessage) → Frontend
 */

const BRIDGE_PREFIX = "partnercalc-cookie-bridge";

// Listen for messages from the frontend page
window.addEventListener("message", async (event) => {
  // Only accept messages from the same window (our frontend page)
  if (event.source !== window) return;
  if (!event.data || event.data.type !== `${BRIDGE_PREFIX}:request`) return;

  const { action, requestId } = event.data;

  try {
    // Forward the request to the background service worker
    const response = await chrome.runtime.sendMessage({ action });

    // Send the response back to the frontend page
    window.postMessage({
      type: `${BRIDGE_PREFIX}:response`,
      requestId,
      success: true,
      data: response
    }, "*");
  } catch (err) {
    window.postMessage({
      type: `${BRIDGE_PREFIX}:response`,
      requestId,
      success: false,
      error: err.message || "Extension communication failed"
    }, "*");
  }
});

// Announce that the bridge is ready (so the frontend knows the extension is installed)
window.postMessage({
  type: `${BRIDGE_PREFIX}:ready`,
  version: chrome.runtime.getManifest().version
}, "*");

console.log("[PartnerCalc Bridge] Content bridge loaded - extension ↔ frontend communication ready");
