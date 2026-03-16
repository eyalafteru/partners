/**
 * PartnerCalc - Facebook Reply Content Script
 * 
 * Runs on Facebook pages when triggered by the background service worker.
 * Receives a reply task, finds the comment, types and submits the reply.
 * Reports results back to background.js which forwards to the backend.
 */

const LOG_PREFIX = "[PartnerCalc Reply]";

function log(level, msg, data) {
  const ts = new Date().toISOString().slice(11, 23);
  const text = `${LOG_PREFIX} ${ts} [${level}] ${msg}`;
  if (data) console[level === "error" ? "error" : "log"](text, data);
  else console[level === "error" ? "error" : "log"](text);

  // Forward to background for backend logging
  try {
    chrome.runtime.sendMessage({
      action: "extensionLog",
      level,
      message: msg,
      replyId: window.__pcReplyTask?.reply_id || null,
    });
  } catch (_) { /* extension context may be invalidated */ }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForSelector(selector, timeout = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const el = document.querySelector(selector);
    if (el) return el;
    await sleep(500);
  }
  return null;
}

async function waitForAnySelector(selectors, timeout = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) return { el, selector: sel };
    }
    await sleep(500);
  }
  return null;
}

// Scroll an element into view with human-like behavior
async function scrollToElement(el) {
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(800 + Math.random() * 400);
}

// Type text character by character with human-like delays
async function humanType(el, text) {
  el.focus();
  await sleep(300);

  log("info", `Typing ${text.length} chars into ${el.isContentEditable ? "contenteditable" : "textarea"}...`);

  if (el.isContentEditable) {
    // Try execCommand first (works when tab is active/focused)
    const testResult = document.execCommand("insertText", false, text.charAt(0));
    await sleep(50);

    const editorHasContent = (el.textContent || "").length > 0;
    if (testResult && editorHasContent) {
      log("info", "execCommand works, typing char-by-char");
      // First char already typed, continue with the rest
      for (let i = 1; i < text.length; i++) {
        document.execCommand("insertText", false, text.charAt(i));
        await sleep(30 + Math.random() * 70);
      }
    } else {
      log("warn", `execCommand failed (returned=${testResult}, content="${el.textContent}"), using clipboard fallback`);
      // Clear any partial content
      el.textContent = "";
      el.focus();
      await sleep(100);

      // Fallback: set textContent + dispatch InputEvent
      el.textContent = text;
      el.dispatchEvent(new InputEvent("input", {
        bubbles: true,
        inputType: "insertText",
        data: text,
      }));
    }
  } else {
    for (const char of text) {
      const prevVal = el.value || "";
      el.value = prevVal + char;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(30 + Math.random() * 70);
    }
  }

  await sleep(200);
  const finalText = el.isContentEditable ? (el.textContent || "") : (el.value || "");
  log("info", `Typing complete. Editor content length: ${finalText.length}`);
}

// Find the comment element by comment ID or commenter name
function findComment(task) {
  log("info", `Looking for comment: id=${task.comment_id}, user=${task.commenter_name}`);

  const allComments = document.querySelectorAll('[role="article"]');
  log("info", `Found ${allComments.length} article elements on page`);

  for (const article of allComments) {
    const text = article.textContent || "";
    // Match by commenter name
    if (task.commenter_name && text.includes(task.commenter_name)) {
      log("info", `Matched comment by commenter name: ${task.commenter_name}`);
      return article;
    }
  }

  // Fallback: try data attributes
  if (task.comment_id) {
    const byAttr = document.querySelector(`[data-commentid="${task.comment_id}"]`);
    if (byAttr) {
      log("info", `Matched comment by data-commentid`);
      return byAttr;
    }
  }

  return null;
}

// Find and click the "Reply" button near a comment
async function clickReplyButton(commentEl) {
  const replySelectors = [
    'div[role="button"]',
    'span[role="button"]',
  ];

  const buttons = commentEl.querySelectorAll('div[role="button"], span[role="button"]');
  for (const btn of buttons) {
    const text = (btn.textContent || "").trim().toLowerCase();
    if (text === "reply" || text === "הגב" || text === "השב" || text === "respond") {
      log("info", `Found reply button with text: "${text}"`);
      await scrollToElement(btn);
      btn.click();
      await sleep(1000 + Math.random() * 500);
      return true;
    }
  }

  log("warn", "No reply button found by text, trying aria-label");
  const ariaButtons = commentEl.querySelectorAll('[aria-label*="Reply"], [aria-label*="הגב"]');
  if (ariaButtons.length > 0) {
    await scrollToElement(ariaButtons[0]);
    ariaButtons[0].click();
    await sleep(1000);
    return true;
  }

  return false;
}

// Find the reply editor (contenteditable or textarea)
async function findReplyEditor() {
  const editorSelectors = [
    'div[contenteditable="true"][role="textbox"][aria-label*="reply" i]',
    'div[contenteditable="true"][role="textbox"][aria-label*="הגב"]',
    'div[contenteditable="true"][role="textbox"][aria-label*="comment" i]',
    'div[contenteditable="true"][role="textbox"][aria-label*="תגובה"]',
    'div[contenteditable="true"][role="textbox"]',
    'textarea[name="comment_text"]',
    'textarea[aria-label*="reply" i]',
    'textarea[aria-label*="comment" i]',
  ];

  const result = await waitForAnySelector(editorSelectors, 10000);
  if (result) {
    log("info", `Found reply editor: ${result.selector}`);
    return result.el;
  }
  return null;
}

// Submit the reply (Enter key or submit button)
async function submitReply(editorEl) {
  log("info", "Submitting reply...");

  // Try pressing Enter (Facebook's default submit)
  editorEl.dispatchEvent(new KeyboardEvent("keydown", {
    key: "Enter", code: "Enter", keyCode: 13, bubbles: true,
  }));
  await sleep(500);

  // Also try finding a submit button nearby
  const submitSelectors = [
    'div[aria-label="Submit"]',
    'div[aria-label="שלח"]',
    'div[aria-label="Post"]',
    'div[aria-label="פרסם"]',
    'div[role="button"][aria-label*="submit" i]',
    'div[role="button"][aria-label*="שלח"]',
  ];

  for (const sel of submitSelectors) {
    const btn = document.querySelector(sel);
    if (btn) {
      log("info", `Found submit button: ${sel}`);
      btn.click();
      await sleep(1000);
      return true;
    }
  }

  log("info", "No explicit submit button, Enter key was sent");
  return true;
}

// Main reply execution flow
async function executeReplyTask(task) {
  log("info", "=== Starting reply task ===", task);

  // Step 1: Wait for page to fully load
  log("info", "Step 1: Waiting for page to stabilize...");
  await sleep(3000 + Math.random() * 2000);

  // Step 2: Find the comment
  log("info", "Step 2: Looking for target comment...");
  const commentEl = findComment(task);
  if (!commentEl) {
    // If we can't find the specific comment, try to reply to the post directly
    log("warn", "Could not find specific comment, trying to post as a general comment");

    const editor = await findReplyEditor();
    if (!editor) {
      return { success: false, error: "Could not find comment or any reply editor on page" };
    }

    log("info", "Found general comment editor, typing reply...");
    await scrollToElement(editor);
    await humanType(editor, task.reply_message);
    log("info", "Typing done, preparing to submit...");
    await sleep(500);
    const submitted = await submitReply(editor);
    log("info", `Submit result: ${submitted}`);
    await sleep(2000);

    return { success: true, method: "general_comment" };
  }

  // Step 3: Click "Reply" button
  log("info", "Step 3: Clicking reply button...");
  await scrollToElement(commentEl);
  const clicked = await clickReplyButton(commentEl);
  if (!clicked) {
    log("warn", "Could not click reply button, trying to find editor anyway");
  }

  // Step 4: Find the reply editor
  log("info", "Step 4: Looking for reply editor...");
  const editor = await findReplyEditor();
  if (!editor) {
    return { success: false, error: "Reply editor not found after clicking reply button" };
  }

  // Step 5: Type the reply with human-like timing
  log("info", `Step 5: Typing reply (${task.reply_message.length} chars)...`);
  await scrollToElement(editor);
  await humanType(editor, task.reply_message);

  // Step 6: Submit
  log("info", "Step 6: Submitting...");
  await sleep(500 + Math.random() * 500);
  await submitReply(editor);

  // Step 7: Verify
  log("info", "Step 7: Waiting for confirmation...");
  await sleep(3000);

  return { success: true, method: "comment_reply" };
}

// Listen for messages from background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "executeReply") {
    window.__pcReplyTask = message.task;

    log("info", `Received reply task for reply_id=${message.task.reply_id}`);

    executeReplyTask(message.task)
      .then(result => {
        log(result.success ? "info" : "error",
          `Task finished: success=${result.success}${result.error ? " error=" + result.error : ""}`
        );
        sendResponse(result);
      })
      .catch(err => {
        log("error", `Task crashed: ${err.message}`);
        sendResponse({ success: false, error: err.message });
      });

    return true; // async response
  }
});
