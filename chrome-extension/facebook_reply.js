/**
 * PartnerCalc - Facebook Reply Content Script
 * 
 * Runs on Facebook pages when triggered by the background service worker.
 * Receives a reply task, finds the comment, types and submits the reply.
 * Reports results back to background.js which forwards to the backend.
 * 
 * Human-like behavior: realistic typing speed, gaussian delays,
 * typo simulation, page reading before commenting, natural mouse clicks.
 */

const LOG_PREFIX = "[PartnerCalc Reply]";

function log(level, msg, data) {
  const ts = new Date().toISOString().slice(11, 23);
  const text = `${LOG_PREFIX} ${ts} [${level}] ${msg}`;
  if (data) console[level === "error" ? "error" : "log"](text, data);
  else console[level === "error" ? "error" : "log"](text);

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

// ========== Realistic Timing Helpers ==========

function gaussianRandom(min, max) {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  let num = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  num = num / 6 + 0.5;
  num = Math.max(0, Math.min(1, num));
  return Math.floor(min + num * (max - min));
}

function randomBetween(min, max) {
  return Math.floor(min + Math.random() * (max - min));
}

// ========== Selectors ==========

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

// ========== Human-like Interactions ==========

async function scrollToElement(el) {
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(gaussianRandom(600, 1200));
}

function simulateClick(el) {
  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width * (0.3 + Math.random() * 0.4);
  const y = rect.top + rect.height * (0.3 + Math.random() * 0.4);

  const eventProps = { bubbles: true, clientX: x, clientY: y };

  el.dispatchEvent(new MouseEvent("mousemove", eventProps));
  el.dispatchEvent(new MouseEvent("mousedown", { ...eventProps, button: 0 }));
  el.dispatchEvent(new MouseEvent("mouseup", { ...eventProps, button: 0 }));
  el.dispatchEvent(new MouseEvent("click", { ...eventProps, button: 0 }));
  el.focus();
}

async function simulateReading() {
  log("info", "Simulating page reading...");

  const scrollDown1 = randomBetween(250, 500);
  window.scrollBy({ top: scrollDown1, behavior: "smooth" });
  await sleep(gaussianRandom(2000, 4000));

  const scrollDown2 = randomBetween(150, 350);
  window.scrollBy({ top: scrollDown2, behavior: "smooth" });
  await sleep(gaussianRandom(1500, 3500));

  const scrollUp = randomBetween(100, 300);
  window.scrollBy({ top: -scrollUp, behavior: "smooth" });
  await sleep(gaussianRandom(1000, 2000));

  log("info", "Reading simulation complete");
}

// Hebrew neighbor keys for typo simulation (standard Israeli keyboard layout)
const HEBREW_NEIGHBORS = {
  "ש": "דג", "ד": "שג", "ג": "שדכ", "כ": "גע", "ע": "כי",
  "י": "עח", "ח": "יל", "ל": "חך", "ך": "לף", "ף": "ך",
  "ק": "רא", "ר": "קא", "א": "רקט", "ט": "אם", "ם": "טו",
  "ו": "םנ", "נ": "וב", "ב": "נה", "ה": "בת", "ת": "הצ",
  "ץ": "ת", "צ": "תז", "ז": "צס", "ס": "זפ", "פ": "ס",
  " ": " ",
};

function getTypoChar(original) {
  const neighbors = HEBREW_NEIGHBORS[original];
  if (neighbors && neighbors.length > 0) {
    return neighbors[Math.floor(Math.random() * neighbors.length)];
  }
  return null;
}

// ========== Human-like Typing ==========

async function humanType(el, text) {
  simulateClick(el);
  await sleep(gaussianRandom(800, 2000));

  log("info", `Typing ${text.length} chars into ${el.isContentEditable ? "contenteditable" : "textarea"}...`);

  if (el.isContentEditable) {
    const testResult = document.execCommand("insertText", false, text.charAt(0));
    await sleep(50);

    const editorHasContent = (el.textContent || "").length > 0;
    if (testResult && editorHasContent) {
      log("info", "execCommand works, typing with human timing");

      for (let i = 1; i < text.length; i++) {
        const char = text[i];
        const prevChar = text[i - 1];

        // Typo simulation: ~4% chance on non-space characters
        if (Math.random() < 0.04 && char !== " " && char !== "\n") {
          const typo = getTypoChar(char);
          if (typo) {
            document.execCommand("insertText", false, typo);
            await sleep(gaussianRandom(80, 200));
            document.execCommand("delete", false, null);
            await sleep(gaussianRandom(60, 150));
          }
        }

        document.execCommand("insertText", false, char);

        // Context-dependent delays
        if (char === " ") {
          await sleep(gaussianRandom(150, 450));
        } else if (".!?".includes(char)) {
          await sleep(gaussianRandom(400, 1100));
        } else if (",;:".includes(char)) {
          await sleep(gaussianRandom(200, 600));
        } else if (char === "\n") {
          await sleep(gaussianRandom(600, 1400));
        } else {
          // Base typing speed, slightly faster after space (start of word burst)
          const isWordStart = prevChar === " " || prevChar === "\n";
          if (isWordStart) {
            await sleep(gaussianRandom(80, 180));
          } else {
            await sleep(gaussianRandom(100, 250));
          }
        }
      }
    } else {
      log("warn", `execCommand failed (returned=${testResult}), using textContent fallback`);
      el.textContent = "";
      el.focus();
      await sleep(100);
      el.textContent = text;
      el.dispatchEvent(new InputEvent("input", {
        bubbles: true,
        inputType: "insertText",
        data: text,
      }));
    }
  } else {
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      el.value = (el.value || "") + char;
      el.dispatchEvent(new Event("input", { bubbles: true }));

      if (char === " ") await sleep(gaussianRandom(150, 450));
      else if (".!?".includes(char)) await sleep(gaussianRandom(400, 1100));
      else await sleep(gaussianRandom(100, 250));
    }
  }

  await sleep(gaussianRandom(800, 2000));
  const finalText = el.isContentEditable ? (el.textContent || "") : (el.value || "");
  log("info", `Typing complete. Editor content length: ${finalText.length}`);
}

// ========== Banner Image Attachment ==========

async function attachBannerImage(editor, bannerType) {
  const bannerUrl = chrome.runtime.getURL(`banners/${bannerType}.png`);
  log("info", `Fetching banner image: ${bannerType} from ${bannerUrl}`);

  const response = await fetch(bannerUrl);
  const blob = await response.blob();
  const file = new File([blob], `${bannerType}.png`, { type: "image/png" });

  // Strategy 1: Paste event on the editor
  log("info", "Trying paste strategy...");
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);

  const pasteEvent = new ClipboardEvent("paste", {
    bubbles: true,
    cancelable: true,
    clipboardData: dataTransfer,
  });
  editor.dispatchEvent(pasteEvent);
  await sleep(3000);

  // Check if image appeared (Facebook shows a preview)
  const preview = document.querySelector('img[src*="blob:"], div[data-visualcompletion] img, div[role="img"]');
  if (preview) {
    log("info", "Banner image attached via paste");
    return true;
  }

  // Strategy 2: Find file input via the camera/photo button
  log("info", "Paste did not work, trying file input strategy...");

  const commentArea = editor.closest('[role="complementary"], form, [data-testid]') || editor.parentElement.parentElement.parentElement;

  // Look for the image/camera button
  const photoButtons = commentArea.querySelectorAll('[aria-label*="photo" i], [aria-label*="תמונה"], [aria-label*="צילום"], [aria-label*="image" i], [aria-label*="GIF"]');
  let fileInput = null;

  if (photoButtons.length > 0) {
    log("info", `Found ${photoButtons.length} photo buttons, clicking first...`);
    simulateClick(photoButtons[0]);
    await sleep(2000);
  }

  // Look for file input that appeared
  const inputs = document.querySelectorAll('input[type="file"][accept*="image"]');
  if (inputs.length > 0) {
    fileInput = inputs[inputs.length - 1];
    log("info", "Found file input, setting files...");

    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    await sleep(3000);

    log("info", "Banner image attached via file input");
    return true;
  }

  // Strategy 3: Drop event
  log("info", "Trying drop strategy...");
  const dropData = new DataTransfer();
  dropData.items.add(file);

  const dropEvent = new DragEvent("drop", {
    bubbles: true,
    cancelable: true,
    dataTransfer: dropData,
  });
  editor.dispatchEvent(dropEvent);
  await sleep(3000);

  log("warn", "All image attachment strategies attempted");
  return false;
}

// ========== Comment Finding ==========

function findComment(task) {
  log("info", `Looking for comment: id=${task.comment_id}, user=${task.commenter_name}`);

  const allComments = document.querySelectorAll('[role="article"]');
  log("info", `Found ${allComments.length} article elements on page`);

  for (const article of allComments) {
    const text = article.textContent || "";
    if (task.commenter_name && text.includes(task.commenter_name)) {
      log("info", `Matched comment by commenter name: ${task.commenter_name}`);
      return article;
    }
  }

  if (task.comment_id) {
    const byAttr = document.querySelector(`[data-commentid="${task.comment_id}"]`);
    if (byAttr) {
      log("info", `Matched comment by data-commentid`);
      return byAttr;
    }
  }

  return null;
}

// ========== Reply Button ==========

async function clickReplyButton(commentEl) {
  const buttons = commentEl.querySelectorAll('div[role="button"], span[role="button"]');
  for (const btn of buttons) {
    const text = (btn.textContent || "").trim().toLowerCase();
    if (text === "reply" || text === "הגב" || text === "השב" || text === "respond") {
      log("info", `Found reply button with text: "${text}"`);
      await scrollToElement(btn);
      simulateClick(btn);
      await sleep(gaussianRandom(1000, 2000));
      return true;
    }
  }

  log("warn", "No reply button found by text, trying aria-label");
  const ariaButtons = commentEl.querySelectorAll('[aria-label*="Reply"], [aria-label*="הגב"]');
  if (ariaButtons.length > 0) {
    await scrollToElement(ariaButtons[0]);
    simulateClick(ariaButtons[0]);
    await sleep(gaussianRandom(1000, 1800));
    return true;
  }

  return false;
}

// ========== Reply Editor ==========

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

// ========== Submit ==========

async function submitReply(editorEl) {
  log("info", "Submitting reply...");

  editorEl.dispatchEvent(new KeyboardEvent("keydown", {
    key: "Enter", code: "Enter", keyCode: 13, bubbles: true,
  }));
  await sleep(500);

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
      simulateClick(btn);
      await sleep(1000);
      return true;
    }
  }

  log("info", "No explicit submit button, Enter key was sent");
  return true;
}

// ========== Main Task Flow ==========

async function executeReplyTask(task) {
  log("info", "=== Starting reply task ===", task);

  // Step 1: Wait for page to fully load
  log("info", "Step 1: Waiting for page to stabilize...");
  await sleep(gaussianRandom(4000, 8000));

  // Step 2: Simulate reading the post and comments
  log("info", "Step 2: Reading the post...");
  await simulateReading();

  // Step 3: Find the comment
  log("info", "Step 3: Looking for target comment...");
  const commentEl = findComment(task);
  if (!commentEl) {
    log("warn", "Could not find specific comment, trying to post as a general comment");

    const editor = await findReplyEditor();
    if (!editor) {
      return { success: false, error: "Could not find comment or any reply editor on page" };
    }

    log("info", "Found general comment editor");
    await scrollToElement(editor);
    await sleep(gaussianRandom(1000, 2500));

    // Banner flow: attach image first, then type text
    if (task.reply_type === "banner" && task.banner_type) {
      log("info", `Banner reply: attaching ${task.banner_type} image...`);
      const attached = await attachBannerImage(editor, task.banner_type);
      if (attached) {
        log("info", "Banner attached, waiting before typing text...");
        await sleep(gaussianRandom(2000, 4000));
      } else {
        log("warn", "Banner attachment failed, continuing with text only");
      }
    }

    await humanType(editor, task.reply_message);
    log("info", "Typing done, reviewing before submit...");
    await sleep(gaussianRandom(1500, 3000));
    const submitted = await submitReply(editor);
    log("info", `Submit result: ${submitted}`);
    await sleep(gaussianRandom(2000, 4000));

    return { success: true, method: "general_comment" };
  }

  // Step 4: Scroll to comment and click Reply
  log("info", "Step 4: Clicking reply button...");
  await scrollToElement(commentEl);
  await sleep(gaussianRandom(500, 1500));
  const clicked = await clickReplyButton(commentEl);
  if (!clicked) {
    log("warn", "Could not click reply button, trying to find editor anyway");
  }

  // Step 5: Find the reply editor
  log("info", "Step 5: Looking for reply editor...");
  const editor = await findReplyEditor();
  if (!editor) {
    return { success: false, error: "Reply editor not found after clicking reply button" };
  }

  // Step 6: Brief pause before typing (thinking what to write)
  log("info", "Step 6: Preparing to type...");
  await scrollToElement(editor);
  await sleep(gaussianRandom(1000, 3000));

  // Step 6.5: Banner flow - attach image before typing
  if (task.reply_type === "banner" && task.banner_type) {
    log("info", `Step 6.5: Attaching banner image (${task.banner_type})...`);
    const attached = await attachBannerImage(editor, task.banner_type);
    if (attached) {
      log("info", "Banner attached, waiting before typing text...");
      await sleep(gaussianRandom(2000, 4000));
    } else {
      log("warn", "Banner attachment failed, continuing with text only");
    }
  }

  // Step 7: Type the reply
  log("info", `Step 7: Typing reply (${task.reply_message.length} chars)...`);
  await humanType(editor, task.reply_message);

  // Step 8: Review before submit
  log("info", "Step 8: Reviewing before submit...");
  await sleep(gaussianRandom(1500, 3000));

  // Step 9: Submit
  log("info", "Step 9: Submitting...");
  await submitReply(editor);

  // Step 10: Wait and verify
  log("info", "Step 10: Waiting for confirmation...");
  await sleep(gaussianRandom(3000, 5000));

  return { success: true, method: "comment_reply" };
}

// ========== Message Listener ==========

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

    return true;
  }
});
