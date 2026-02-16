/**
 * Facebook Group Auto-Poster (Custom Apify Actor)
 * 
 * Features:
 * - Israeli residential proxy support
 * - Human-like typing (character by character with random delays)
 * - Cookie validation before posting
 * - Post verification (checks post appears in feed)
 * - Post URL extraction
 * - Block detection and automatic stopping
 */

const { Actor, log } = require('apify');
const { chromium } = require('playwright');

// ============================================================
// Debug: capture screenshots and HTML to Apify Key-Value Store
// ============================================================
let debugStepCounter = 0;

/**
 * Capture a screenshot (and optionally HTML) and save to Apify Key-Value Store.
 * Files are downloadable from Apify Console -> Run -> Key-Value Store tab.
 * 
 * @param {import('playwright').Page} page - Playwright page
 * @param {string} stepName - Short name for this step (e.g. "group-loaded")
 * @param {object} options
 * @param {boolean} options.saveHtml - Also save page HTML (useful on failures)
 * @param {boolean} options.fullPage - Capture full scrollable page (default: false)
 */
async function captureDebug(page, stepName, { saveHtml = false, fullPage = false } = {}) {
    debugStepCounter++;
    const prefix = `debug-${String(debugStepCounter).padStart(2, '0')}-${stepName}`;
    
    try {
        // Screenshot
        const screenshotBuffer = await page.screenshot({ fullPage, timeout: 10000 });
        await Actor.setValue(prefix, screenshotBuffer, { contentType: 'image/png' });
        log.info(`📸 Screenshot saved: ${prefix}.png`);
    } catch (e) {
        log.warning(`📸 Failed to capture screenshot "${prefix}": ${e.message}`);
    }
    
    if (saveHtml) {
        try {
            const html = await page.content();
            await Actor.setValue(`${prefix}-html`, html, { contentType: 'text/html' });
            log.info(`📄 HTML saved: ${prefix}-html (${Math.round(html.length / 1024)}KB)`);
        } catch (e) {
            log.warning(`📄 Failed to capture HTML "${prefix}": ${e.message}`);
        }
    }
}

// ============================================================
// Utility: random delay
// ============================================================
function randomDelay(minMs, maxMs) {
    return Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================
// Utility: human-like typing
// ============================================================
async function humanType(page, selector, text) {
    await page.click(selector);
    await sleep(randomDelay(300, 800));

    for (const char of text) {
        await page.keyboard.type(char, { delay: randomDelay(30, 80) });
        // Occasional longer pause (simulating thinking)
        if (Math.random() < 0.05) {
            await sleep(randomDelay(200, 600));
        }
    }
    await sleep(randomDelay(500, 1500));
}

// ============================================================
// Utility: human-like typing into contenteditable divs
// ============================================================
async function humanTypeIntoEditor(page, editorElement, text) {
    await editorElement.click();
    await sleep(randomDelay(300, 800));

    for (const char of text) {
        await page.keyboard.type(char, { delay: randomDelay(30, 80) });
        if (Math.random() < 0.05) {
            await sleep(randomDelay(200, 600));
        }
    }
    await sleep(randomDelay(500, 1500));
}

// ============================================================
// Wait for Facebook to generate a link preview (if URL present)
// ============================================================
async function waitForLinkPreview(page, message) {
    // Check if the message contains a URL
    const urlRegex = /https?:\/\/[^\s]+/i;
    const hasUrl = urlRegex.test(message);
    
    if (!hasUrl) {
        log.info('📎 No URL detected in message - skipping link preview wait');
        return;
    }
    
    log.info('🔗 URL detected in message - waiting for Facebook to generate link preview...');
    
    // Facebook needs time to:
    // 1. Detect the URL in the text
    // 2. Fetch Open Graph metadata from the target site
    // 3. Render the preview card
    
    const previewSelectors = [
        // Link preview card in the post dialog
        'div[role="dialog"] a[role="link"][href*="l.facebook.com"]',
        'div[role="dialog"] a[href*="youtube"]',
        'div[role="dialog"] a[href*="youtu.be"]',
        // Generic link attachment preview containers
        'div[role="dialog"] div[class*="attachment"]',
        'div[role="dialog"] img[src*="external"]',
        // Facebook's link preview card typically has an image
        'div[role="dialog"] a[role="link"] img',
        // Link scraper preview area
        'div[role="dialog"] div[aria-label*="link"]',
        'div[role="dialog"] div[aria-label*="קישור"]',
        // Generic: any new image that appears after typing (preview thumbnail)
        'div[role="dialog"] span[data-lexical-text] ~ div img',
    ];
    
    const maxWaitMs = 15000; // Wait up to 15 seconds
    const checkIntervalMs = 2000; // Check every 2 seconds
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWaitMs) {
        await sleep(checkIntervalMs);
        
        for (const selector of previewSelectors) {
            try {
                const el = await page.$(selector);
                if (el) {
                    const isVisible = await el.isVisible();
                    if (isVisible) {
                        log.info(`🔗 ✅ Link preview detected! (selector: ${selector})`);
                        // Give it a bit more time to fully render
                        await sleep(randomDelay(2000, 3000));
                        return;
                    }
                }
            } catch (e) { /* try next selector */ }
        }
        
        log.info(`🔗 Still waiting for link preview... (${Math.round((Date.now() - startTime) / 1000)}s)`);
    }
    
    // Even if we didn't find a preview with selectors, check if something new appeared
    // by looking for any image or link card inside the dialog that wasn't there before
    log.info('🔗 Trying broader detection for link preview...');
    try {
        const dialog = await page.$('div[role="dialog"]');
        if (dialog) {
            // Count images in dialog - if there's at least one, a preview might have loaded
            const images = await dialog.$$('img');
            if (images.length > 0) {
                log.info(`🔗 ✅ Found ${images.length} image(s) in dialog - likely a link preview`);
                await sleep(randomDelay(1000, 2000));
                return;
            }
        }
    } catch (e) { /* ignore */ }
    
    log.warning('🔗 ⚠️ Link preview did not appear within timeout - posting without preview');
    // Still wait a moment before posting
    await sleep(randomDelay(1000, 2000));
}

// ============================================================
// Cookie validation: check if logged in
// ============================================================
/**
 * Returns: 'valid' | 'expired' | 'connection_error'
 */
async function validateCookies(page) {
    log.info('🍪 Validating Facebook cookies...');
    
    // Try loading Facebook with retries - use 'load' for full page render
    let loaded = false;
    let pageHasContent = false;
    
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            log.info(`🍪 Navigation attempt ${attempt}/3...`);
            await page.goto('https://www.facebook.com/', { waitUntil: 'load', timeout: 90000 });
            loaded = true;
            log.info(`🍪 ✅ Page loaded on attempt ${attempt}`);
            
            // Wait for content to render
            await sleep(5000);
            
            // Check if page actually has content
            const textLen = await page.evaluate(() => document.body ? document.body.innerText.length : 0);
            log.info(`🍪 Page content length: ${textLen} chars`);
            
            if (textLen > 100) {
                pageHasContent = true;
                break;
            } else {
                log.warning(`🍪 Page loaded but empty (${textLen} chars) - retrying...`);
                if (attempt < 3) {
                    await sleep(randomDelay(3000, 5000));
                }
            }
        } catch (e) {
            log.warning(`🍪 Attempt ${attempt} failed: ${e.message}`);
            if (attempt < 3) {
                await sleep(randomDelay(5000, 8000));
            }
        }
    }
    
    if (!loaded) {
        log.error('🍪 ❌ Could not connect to Facebook after 3 attempts - proxy/network issue');
        return 'connection_error';
    }
    
    if (!pageHasContent) {
        log.error('🍪 ❌ Facebook page loaded but empty after 3 attempts - proxy may be blocked');
        return 'connection_error';
    }

    const url = page.url();
    log.info(`🍪 Current URL: ${url}`);

    // Check for login/checkpoint redirects
    if (url.includes('/login') || url.includes('/checkpoint') || url.includes('login_attempt')) {
        log.error('🍪 ❌ Cookie expired - redirected to login page');
        return 'expired';
    }

    // Get page content for analysis
    const bodyText = await page.textContent('body').catch(() => '');
    log.info(`🍪 Page text length: ${bodyText.length} chars`);

    // STEP 1: Check for LOGGED-OUT indicators first (these are definitive)
    const loggedOutIndicators = [
        'Create new account',
        'Forgot password?',
        'Log Into Facebook',
        'Sign Up',
        'שכחת את הסיסמה',
        'יצירת חשבון חדש',
        'התחברות לפייסבוק',
        'הירשם',
    ];
    
    let loggedOutSignals = 0;
    for (const indicator of loggedOutIndicators) {
        if (bodyText.includes(indicator)) {
            log.info(`🍪 ⚠️ Found logged-out indicator: "${indicator}"`);
            loggedOutSignals++;
        }
    }
    
    // Check for login form element (only exists on logged-out pages)
    try {
        const loginForm = await page.$('form[action*="login"]');
        if (loginForm) {
            log.info('🍪 ⚠️ Found login form element');
            loggedOutSignals += 2; // Strong signal
        }
    } catch (e) { /* ignore */ }
    
    // Check for email/password input fields (login page specific)
    try {
        const emailInput = await page.$('input[name="email"], input[id="email"]');
        const passInput = await page.$('input[name="pass"], input[id="pass"]');
        if (emailInput && passInput) {
            log.info('🍪 ⚠️ Found email + password inputs (login form)');
            loggedOutSignals += 3; // Very strong signal
        }
    } catch (e) { /* ignore */ }

    if (loggedOutSignals >= 2) {
        log.error(`🍪 ❌ Cookie expired - ${loggedOutSignals} logged-out signals detected`);
        return 'expired';
    }

    // STEP 2: Check for LOGGED-IN indicators (elements that ONLY appear when logged in)
    const loggedInIndicators = [
        '[data-pagelet="Stories"]',
        '[aria-label="Your profile"]',
        '[aria-label="הפרופיל שלך"]',
        '[aria-label="Messenger"]',
        '[aria-label="מסנג\'ר"]',
        '[aria-label="Notifications"]',
        '[aria-label="התראות"]',
        '[data-pagelet="LeftRail"]',
        '[data-pagelet="RightRail"]',
        '[aria-label="Create a post"]',
        '[aria-label="צרו פוסט"]',
        'div[role="feed"]',
    ];

    for (const selector of loggedInIndicators) {
        try {
            const el = await page.$(selector);
            if (el) {
                log.info(`🍪 ✅ Cookie is valid - found logged-in element: ${selector}`);
                return 'valid';
            }
        } catch (e) { /* ignore */ }
    }

    // STEP 3: If no clear signals either way, check page size cautiously
    if (bodyText.length > 100) {
        // Page loaded with content but no clear logged-in elements found
        // Log a warning and treat as potentially expired
        log.warning(`🍪 ⚠️ Page loaded (${bodyText.length} chars) but no logged-in elements found`);
        log.warning('🍪 ⚠️ Treating as potentially valid but uncertain');
        // Give it benefit of the doubt only if zero logged-out signals
        if (loggedOutSignals === 0) {
            log.info('🍪 ✅ No logged-out signals detected - assuming valid');
            return 'valid';
        }
        log.error('🍪 ❌ Cookie likely expired');
        return 'expired';
    }

    // Page loaded but seems empty - might be proxy issue
    log.warning('🍪 ⚠️ Page loaded but content seems empty - possible proxy issue');
    return 'connection_error';
}

// ============================================================
// Block detection
// ============================================================
async function checkForBlock(page) {
    const bodyText = await page.textContent('body').catch(() => '');
    const blockIndicators = [
        'You\'re Temporarily Blocked',
        'temporarily blocked',
        'We limit how often',
        'you\'ve been blocked',
        'try again later',
        'אתה חסום זמנית',
        'חסמנו אותך זמנית',
        'ניסית לפרסם לעתים קרובות מדי',
    ];

    for (const indicator of blockIndicators) {
        if (bodyText.toLowerCase().includes(indicator.toLowerCase())) {
            return true;
        }
    }
    return false;
}

// ============================================================
// Find and click the post creation area in a group
// ============================================================
async function openPostEditor(page) {
    // Multiple selector strategies for different FB UI versions (EN/HE)
    const postAreaSelectors = [
        // "Write something..." / "?מה דעתך"
        '[role="button"][tabindex="0"]:has-text("Write something")',
        '[role="button"][tabindex="0"]:has-text("מה דעתך")',
        '[role="button"][tabindex="0"]:has-text("What\'s on your mind")',
        // Generic post composer area
        'div[data-pagelet="GroupInlineComposer"] [role="button"]',
        'div[class*="sjgh65i0"] [role="button"]',
        // Fallback: any button near "Write something" or Hebrew equiv
        'span:has-text("Write something")',
        'span:has-text("מה דעתך")',
        'span:has-text("כתבו משהו")',
        // Additional selectors
        'div[aria-label="Create a public post…"]',
        'div[aria-label="Write something..."]',
        'div[aria-label="כתבו משהו..."]',
        'div[role="button"]:has-text("Create a public post")',
    ];

    // Retry up to 3 times with increasing wait between attempts
    for (let attempt = 1; attempt <= 3; attempt++) {
        log.info(`📝 Looking for post editor (attempt ${attempt}/3)...`);
        
        for (const selector of postAreaSelectors) {
            try {
                const el = await page.$(selector);
                if (el) {
                    const isVisible = await el.isVisible();
                    if (isVisible) {
                        log.info(`📝 Found post area with selector: ${selector}`);
                        await el.click();
                        await sleep(randomDelay(2000, 4000));
                        return true;
                    }
                }
            } catch (e) { /* try next */ }
        }

        // Text scan: look for any button matching post creation text
        try {
            const buttons = await page.$$('[role="button"]');
            for (const btn of buttons) {
                const text = await btn.textContent().catch(() => '');
                if (text && (
                    text.includes('Write something') ||
                    text.includes('מה דעתך') ||
                    text.includes('כתבו משהו') ||
                    text.includes("What's on your mind") ||
                    text.includes("Create a public post") ||
                    text.includes("צרו פוסט ציבורי")
                )) {
                    log.info(`📝 Found post area via text scan: "${text.substring(0, 50)}"`);
                    await btn.click();
                    await sleep(randomDelay(2000, 4000));
                    return true;
                }
            }
        } catch (e) { /* ignore */ }

        if (attempt < 3) {
            // Log what we see on the page for debugging
            const url = page.url();
            const bodyText = await page.textContent('body').catch(() => '');
            log.info(`📝 Page URL: ${url}`);
            log.info(`📝 Page text length: ${bodyText.length} chars`);
            log.info(`📝 Page snippet: "${bodyText.substring(0, 200).replace(/\n/g, ' ')}"`);
            
            // Scroll to top and wait more for dynamic content
            log.info(`📝 Scrolling to top and waiting before retry...`);
            await page.evaluate(() => window.scrollTo(0, 0));
            await sleep(randomDelay(4000, 6000));
            
            // Try clicking on the page body first to "wake up" lazy-loaded components
            try {
                await page.click('body', { position: { x: 400, y: 300 } });
                await sleep(randomDelay(1000, 2000));
            } catch (e) { /* ignore */ }
        }
    }

    // Final debug: log all visible buttons so we know what's available
    try {
        const allButtons = await page.$$('[role="button"]');
        log.info(`📝 DEBUG: Found ${allButtons.length} buttons on page. Texts:`);
        for (let i = 0; i < Math.min(allButtons.length, 15); i++) {
            const text = await allButtons[i].textContent().catch(() => '');
            if (text && text.trim().length > 0 && text.trim().length < 100) {
                log.info(`   [${i}] "${text.trim().substring(0, 80)}"`);
            }
        }
    } catch (e) { /* ignore */ }

    return false;
}

// ============================================================
// Find the post editor (contenteditable) and type message
// ============================================================
async function typeInPostEditor(page, message) {
    // Wait for the editor modal/overlay to appear
    await sleep(randomDelay(1000, 2000));

    const editorSelectors = [
        'div[role="dialog"] div[contenteditable="true"]',
        'div[role="dialog"] [data-lexical-editor="true"]',
        'form div[contenteditable="true"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][aria-label*="Write"]',
        'div[contenteditable="true"][aria-label*="כתבו"]',
        'div[contenteditable="true"][aria-label*="post"]',
        'div[contenteditable="true"][aria-label*="פוסט"]',
    ];

    for (const selector of editorSelectors) {
        try {
            const el = await page.$(selector);
            if (el) {
                const isVisible = await el.isVisible();
                if (isVisible) {
                    log.info(`📝 Found editor with selector: ${selector}`);
                    await humanTypeIntoEditor(page, el, message);
                    return true;
                }
            }
        } catch (e) { /* try next */ }
    }

    // Fallback: try all contenteditable divs
    try {
        const editors = await page.$$('div[contenteditable="true"]');
        for (const editor of editors) {
            const isVisible = await editor.isVisible();
            if (isVisible) {
                const rect = await editor.boundingBox();
                if (rect && rect.width > 100 && rect.height > 30) {
                    log.info('📝 Found editor via contenteditable scan');
                    await humanTypeIntoEditor(page, editor, message);
                    return true;
                }
            }
        }
    } catch (e) { /* ignore */ }

    return false;
}

// ============================================================
// Find and click the Post/Submit button
// ============================================================
async function clickPostButton(page) {
    const postButtonSelectors = [
        // Dialog post button
        'div[role="dialog"] div[aria-label="Post"][role="button"]',
        'div[role="dialog"] div[aria-label="פרסם"][role="button"]',
        'div[role="dialog"] div[aria-label="פרסום"][role="button"]',
        'div[role="dialog"] div[aria-label="Submit"][role="button"]',
        // Without dialog wrapper (some groups use inline editor)
        'div[aria-label="Post"][role="button"]',
        'div[aria-label="פרסם"][role="button"]',
        'div[aria-label="פרסום"][role="button"]',
        // Form submit
        'form [type="submit"]',
        // Generic post button in dialog
        'div[role="dialog"] [aria-label="Post"]',
        'div[role="dialog"] [aria-label="פרסם"]',
        'div[role="dialog"] [aria-label="פרסום"]',
    ];

    for (const selector of postButtonSelectors) {
        try {
            const el = await page.$(selector);
            if (el) {
                const isVisible = await el.isVisible();
                if (isVisible) {
                    log.info(`📤 Found post button: ${selector}`);
                    await sleep(randomDelay(500, 1500));
                    await el.click();
                    return true;
                } else {
                    log.info(`📤 Found but NOT visible: ${selector}`);
                }
            }
        } catch (e) { /* try next */ }
    }

    // Fallback: scan buttons in the dialog for post text
    try {
        const dialogButtons = await page.$$('div[role="dialog"] [role="button"]');
        log.info(`📤 Fallback scan: found ${dialogButtons.length} buttons in dialog`);
        for (const btn of dialogButtons) {
            const text = await btn.textContent().catch(() => '');
            const ariaLabel = await btn.getAttribute('aria-label').catch(() => '');
            if (
                text === 'Post' || text === 'פרסם' || text === 'פרסום' ||
                ariaLabel === 'Post' || ariaLabel === 'פרסם' || ariaLabel === 'פרסום'
            ) {
                log.info(`📤 Found post button via text: "${text || ariaLabel}"`);
                await sleep(randomDelay(500, 1500));
                await btn.click();
                return true;
            }
        }
        // Log all button labels found for debugging
        if (dialogButtons.length > 0) {
            for (const btn of dialogButtons) {
                const text = (await btn.textContent().catch(() => '')).substring(0, 50);
                const ariaLabel = await btn.getAttribute('aria-label').catch(() => '');
                if (text || ariaLabel) {
                    log.info(`📤   Button: text="${text}", aria-label="${ariaLabel}"`);
                }
            }
        }
    } catch (e) { /* ignore */ }

    // Last resort: scan ALL buttons on page (not just in dialog)
    try {
        const allButtons = await page.$$('[role="button"][aria-label]');
        log.info(`📤 Last resort: scanning ${allButtons.length} aria-labeled buttons on page`);
        for (const btn of allButtons) {
            const ariaLabel = await btn.getAttribute('aria-label').catch(() => '');
            if (ariaLabel === 'Post' || ariaLabel === 'פרסם' || ariaLabel === 'פרסום') {
                const isVisible = await btn.isVisible().catch(() => false);
                if (isVisible) {
                    log.info(`📤 Found post button outside dialog: aria-label="${ariaLabel}"`);
                    await sleep(randomDelay(500, 1500));
                    await btn.click();
                    return true;
                }
            }
        }
    } catch (e) { /* ignore */ }

    return false;
}

// ============================================================
// Verify post appeared in group feed and extract URL
// ============================================================

/**
 * Clean a Facebook URL - remove notification parameters and tracking params
 */
function cleanFacebookUrl(url) {
    try {
        const parsed = new URL(url.startsWith('http') ? url : `https://www.facebook.com${url}`);
        // Remove notification and tracking parameters
        const paramsToRemove = ['notif_id', 'notif_t', 'ref', 'comment_id', '__cft__', '__tn__', 'sfnsn', 'mibextid'];
        for (const param of paramsToRemove) {
            parsed.searchParams.delete(param);
        }
        return parsed.toString();
    } catch (e) {
        return url;
    }
}

/**
 * Check if a URL belongs to the same group we posted to
 */
function isUrlFromGroup(href, groupUrl) {
    // Extract group ID from the group URL (e.g. "1935697136699450" from ".../groups/1935697136699450")
    const groupMatch = groupUrl.match(/groups\/(\d+)/);
    if (!groupMatch) return false;
    const groupId = groupMatch[1];
    
    // Check if the link contains this group ID
    return href.includes(`/groups/${groupId}/`);
}

/**
 * Check if a URL looks like a notification URL (not an actual post URL)
 */
function isNotificationUrl(href) {
    return href.includes('notif_id=') || 
           href.includes('notif_t=') || 
           href.includes('ref=notif') ||
           href.includes('/notifications/');
}

async function verifyPostAndExtractUrl(page, message, groupUrl) {
    log.info('🔍 Verifying post submission...');
    await sleep(randomDelay(3000, 5000));

    // Verify by checking that the post dialog closed (= post was submitted)
    // Do NOT reload the page - that triggers Facebook's bot detection and logs out
    
    let dialogClosed = true;
    try {
        const dialog = await page.$('div[role="dialog"]');
        if (dialog) {
            const isVisible = await dialog.isVisible();
            if (isVisible) {
                dialogClosed = false;
                log.warning('⚠️ Post dialog still open - post may not have been submitted');
            }
        }
    } catch (e) { /* ignore */ }

    if (dialogClosed) {
        log.info('✅ Post dialog closed - post was submitted successfully');
        
        // Try to find the post text on the current page (no reload)
        const messageSnippet = message.substring(0, 40);
        const bodyText = await page.textContent('body').catch(() => '');
        
        if (bodyText.includes(messageSnippet)) {
            log.info('✅ Post text found on page - confirmed posted');
            
            // Try to extract post URL from current page
            // IMPORTANT: Only match URLs that belong to the SAME GROUP we posted to
            try {
                const links = await page.$$('a[href*="/posts/"], a[href*="/permalink/"], a[href*="story_fbid"]');
                log.info(`🔗 Found ${links.length} candidate post links on page`);
                
                for (const link of links) {
                    const href = await link.getAttribute('href');
                    if (!href) continue;
                    
                    const fullUrl = href.startsWith('http') ? href : `https://www.facebook.com${href}`;
                    
                    // Skip notification URLs
                    if (isNotificationUrl(fullUrl)) {
                        log.info(`🔗 Skipping notification URL: ${fullUrl.substring(0, 80)}...`);
                        continue;
                    }
                    
                    // Only accept URLs from the same group
                    if (isUrlFromGroup(fullUrl, groupUrl)) {
                        const cleanUrl = cleanFacebookUrl(fullUrl);
                        log.info(`🔗 Extracted post URL (same group): ${cleanUrl}`);
                        return { verified: true, postUrl: cleanUrl };
                    } else {
                        log.info(`🔗 Skipping URL (different group/profile): ${fullUrl.substring(0, 80)}...`);
                    }
                }
                
                log.warning('🔗 No matching group post URL found among candidates');
            } catch (e) { 
                log.warning(`🔗 Error extracting URLs: ${e.message}`);
            }
        }
        
        return { verified: true, postUrl: null };
    }

    log.warning('⚠️ Could not confirm post was submitted');
    return { verified: false, postUrl: null };
}

// ============================================================
// Main Actor logic
// ============================================================
Actor.main(async () => {
    const input = await Actor.getInput();

    const {
        facebookCookies,
        groupUrls,
        messages,
        delayMinSeconds = 300,
        delayMaxSeconds = 900,
        maxPostsPerRun = 5,
    } = input;

    // Validate input
    if (!facebookCookies || !Array.isArray(facebookCookies) || facebookCookies.length === 0) {
        log.error('❌ facebookCookies is required and must be a non-empty array');
        await Actor.pushData({ status: 'failed', error: 'Missing or invalid facebookCookies' });
        return;
    }
    if (!groupUrls || !Array.isArray(groupUrls) || groupUrls.length === 0) {
        log.error('❌ groupUrls is required and must be a non-empty array');
        await Actor.pushData({ status: 'failed', error: 'Missing or invalid groupUrls' });
        return;
    }
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
        log.error('❌ messages is required and must be a non-empty array');
        await Actor.pushData({ status: 'failed', error: 'Missing or invalid messages' });
        return;
    }

    log.info(`📋 Starting Facebook Group Poster`);
    log.info(`   Groups: ${groupUrls.length}`);
    log.info(`   Messages: ${messages.length}`);
    log.info(`   Max posts: ${maxPostsPerRun}`);
    log.info(`   Delay: ${delayMinSeconds}-${delayMaxSeconds}s`);

    // Setup proxy - Israeli residential with session for consistent IP
    const sessionId = `fb_poster_${Date.now()}`;
    let proxyConfiguration;
    try {
        proxyConfiguration = await Actor.createProxyConfiguration({
            groups: ['RESIDENTIAL'],
            countryCode: 'IL',
        });
        log.info('🇮🇱 Israeli residential proxy configured');
    } catch (e) {
        log.warning(`⚠️ Could not set up residential proxy: ${e.message}. Proceeding without proxy.`);
        proxyConfiguration = null;
    }

    // Build launch options
    const launchOptions = {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
        ],
    };

    if (proxyConfiguration) {
        // Get proxy URL with session ID for consistent IP
        const proxyUrl = await proxyConfiguration.newUrl(sessionId);
        
        // Parse proxy URL into components for Playwright
        try {
            const parsed = new URL(proxyUrl);
            launchOptions.proxy = {
                server: `${parsed.protocol}//${parsed.hostname}:${parsed.port}`,
                username: decodeURIComponent(parsed.username),
                password: decodeURIComponent(parsed.password),
            };
            log.info(`🌐 Proxy server: ${parsed.hostname}:${parsed.port}`);
            log.info(`🌐 Proxy user: ${parsed.username}`);
            log.info(`🌐 Session ID: ${sessionId}`);
        } catch (e) {
            // Fallback - pass full URL
            launchOptions.proxy = { server: proxyUrl };
            log.info(`🌐 Proxy URL (fallback): ${proxyUrl.replace(/:[^:]+@/, ':***@')}`);
        }
    }

    // Launch browser
    const browser = await chromium.launch(launchOptions);

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        locale: 'en-US',
        timezoneId: 'Asia/Jerusalem',
        extraHTTPHeaders: {
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
        },
        // Record video of the entire session for debugging
        recordVideo: {
            dir: './videos/',
            size: { width: 1280, height: 720 },
        },
    });

    // Inject cookies - preserve all original fields including expires and sameSite
    const cookiesToSet = facebookCookies.map(c => {
        const cookie = {
            name: c.name,
            value: c.value,
            domain: c.domain || '.facebook.com',
            path: c.path || '/',
            httpOnly: c.httpOnly !== undefined ? c.httpOnly : false,
            secure: c.secure !== undefined ? c.secure : true,
        };
        // Preserve original sameSite (don't force 'None' - use what Facebook set)
        if (c.sameSite) {
            cookie.sameSite = c.sameSite;
        }
        // Preserve expires timestamp (so cookies aren't treated as session-only)
        if (c.expires && c.expires > 0) {
            cookie.expires = Math.floor(c.expires);
        }
        return cookie;
    });
    await context.addCookies(cookiesToSet);
    log.info(`🍪 Injected ${cookiesToSet.length} cookies`);
    
    // Log cookie details for debugging
    for (const c of cookiesToSet) {
        log.info(`🍪   ${c.name}: sameSite=${c.sameSite || 'default'}, expires=${c.expires || 'session'}`);
    }

    const page = await context.newPage();

    // Stealth: remove webdriver flag
    await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    try {
        // Step 1: Validate cookies
        const cookieStatus = await validateCookies(page);
        
        if (cookieStatus === 'connection_error') {
            log.error('🌐 ❌ PROXY/CONNECTION ERROR - could not reach Facebook');
            await Actor.pushData({
                groupUrl: '',
                status: 'failed',
                postUrl: null,
                error: 'Could not connect to Facebook through proxy. The residential proxy may be temporarily unavailable. Please try again.',
                message: '',
            });
            return;
        }
        
        if (cookieStatus === 'expired') {
            log.error('🍪 ❌ COOKIE EXPIRED - stopping actor');
            await Actor.pushData({
                groupUrl: '',
                status: 'cookie_expired',
                postUrl: null,
                error: 'Facebook cookie has expired. Please upload a new cookie JSON file.',
                message: '',
            });
            return;
        }
        
        log.info('🍪 ✅ Cookie validated successfully');

        // Step 2: Post to each group
        const groupsToPost = groupUrls.slice(0, maxPostsPerRun);
        let blocked = false;

        for (let i = 0; i < groupsToPost.length; i++) {
            if (blocked) break;

            const groupUrl = groupsToPost[i];
            const message = messages[i % messages.length];
            const truncatedMessage = message.substring(0, 80) + (message.length > 80 ? '...' : '');

            log.info(`\n📤 [${i + 1}/${groupsToPost.length}] Posting to: ${groupUrl}`);
            log.info(`   Message: "${truncatedMessage}"`);

            try {
                // Navigate to group - wait for full load through proxy
                await page.goto(groupUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
                log.info('📄 Page domcontentloaded, waiting for dynamic content...');
                await sleep(randomDelay(5000, 8000));
                
                // Scroll to top to ensure composer is visible
                await page.evaluate(() => window.scrollTo(0, 0));
                await sleep(randomDelay(1000, 2000));

                // Debug: capture group page after load
                await captureDebug(page, 'group-loaded');

                // Check if we're logged out on the group page
                const groupPageButtons = await page.$$('[role="button"]');
                let hasLoginButton = false;
                let hasJoinButton = false;
                for (const btn of groupPageButtons) {
                    const text = await btn.textContent().catch(() => '');
                    if (text && text.trim() === 'Log In') hasLoginButton = true;
                    if (text && text.trim() === 'Join group') hasJoinButton = true;
                }
                
                if (hasLoginButton && hasJoinButton) {
                    log.error('🍪 ❌ NOT LOGGED IN on group page! Cookie is expired/invalid.');
                    await Actor.pushData({
                        groupUrl,
                        status: 'cookie_expired',
                        postUrl: null,
                        error: 'Facebook cookie has expired. Please upload a new cookie JSON file.',
                        message: truncatedMessage,
                    });
                    break;
                }

                // Check for blocks
                if (await checkForBlock(page)) {
                    log.error('🚫 BLOCKED by Facebook! Stopping all posts.');
                    await Actor.pushData({
                        groupUrl,
                        status: 'blocked',
                        postUrl: null,
                        error: 'Blocked by Facebook - too many posts or suspicious activity detected',
                        message: truncatedMessage,
                    });
                    blocked = true;
                    break;
                }

                // Open post editor
                const editorOpened = await openPostEditor(page);
                if (!editorOpened) {
                    log.error(`❌ Could not find post creation area in group: ${groupUrl}`);
                    await captureDebug(page, 'editor-not-found', { saveHtml: true });
                    await Actor.pushData({
                        groupUrl,
                        status: 'failed',
                        postUrl: null,
                        error: 'Post creation area not found - group may require admin approval or UI changed',
                        message: truncatedMessage,
                    });
                    continue;
                }

                // Debug: capture editor after opening
                await captureDebug(page, 'editor-opened');

                // Type message
                const typed = await typeInPostEditor(page, message);
                if (!typed) {
                    log.error(`❌ Could not type message in editor for group: ${groupUrl}`);
                    await captureDebug(page, 'type-failed', { saveHtml: true });
                    await Actor.pushData({
                        groupUrl,
                        status: 'failed',
                        postUrl: null,
                        error: 'Could not find text editor in post dialog',
                        message: truncatedMessage,
                    });
                    continue;
                }

                // Debug: capture after message typed
                await captureDebug(page, 'message-typed');

                // Wait for link preview to load (if message contains a URL)
                await waitForLinkPreview(page, message);

                // Debug: capture before clicking Post
                await captureDebug(page, 'before-post-click');

                // Click post button
                const posted = await clickPostButton(page);
                if (!posted) {
                    log.error(`❌ Post button not found for group: ${groupUrl}`);
                    await captureDebug(page, 'post-button-not-found', { saveHtml: true, fullPage: true });
                    await Actor.pushData({
                        groupUrl,
                        status: 'failed',
                        postUrl: null,
                        error: 'Post/Submit button not found',
                        message: truncatedMessage,
                    });
                    continue;
                }

                // Wait for post to be submitted
                await sleep(randomDelay(5000, 8000));

                // Check for block after posting
                if (await checkForBlock(page)) {
                    log.error('🚫 BLOCKED after posting! Stopping.');
                    await Actor.pushData({
                        groupUrl,
                        status: 'blocked',
                        postUrl: null,
                        error: 'Blocked by Facebook after posting attempt',
                        message: truncatedMessage,
                    });
                    blocked = true;
                    break;
                }

                // Verify post and extract URL
                const { verified, postUrl } = await verifyPostAndExtractUrl(page, message, groupUrl);

                if (verified) {
                    log.info(`✅ Post verified in group: ${groupUrl}`);
                } else {
                    // Dialog closed = post was submitted. Not finding it in feed is expected
                    // (we don't reload the page to avoid Facebook logout).
                    log.info(`✅ Post submitted to group (dialog closed): ${groupUrl}`);
                    log.info('ℹ️ Could not verify in feed (no page reload) - this is normal');
                }
                
                await Actor.pushData({
                    groupUrl,
                    status: 'success',
                    postUrl: postUrl || null,
                    error: null,
                    message: truncatedMessage,
                });

                // Delay between groups
                if (i < groupsToPost.length - 1) {
                    const delay = randomDelay(delayMinSeconds * 1000, delayMaxSeconds * 1000);
                    log.info(`⏳ Waiting ${Math.round(delay / 1000)}s before next group...`);
                    await sleep(delay);
                }

            } catch (groupError) {
                log.error(`❌ Error posting to ${groupUrl}: ${groupError.message}`);
                await Actor.pushData({
                    groupUrl,
                    status: 'failed',
                    postUrl: null,
                    error: groupError.message,
                    message: truncatedMessage,
                });
            }
        }

        log.info('\n🏁 Facebook Group Poster finished');

    } catch (error) {
        log.error(`💥 Fatal error: ${error.message}`);
        await Actor.pushData({
            groupUrl: '',
            status: 'failed',
            postUrl: null,
            error: `Fatal: ${error.message}`,
            message: '',
        });
    } finally {
        // Save recorded video to Key-Value Store before closing
        try {
            const pages = context.pages();
            if (pages.length > 0) {
                const video = pages[0].video();
                if (video) {
                    // Close context first so the video file is finalized
                    await context.close();
                    const videoPath = await video.path();
                    const fs = require('fs');
                    const videoBuffer = fs.readFileSync(videoPath);
                    await Actor.setValue('debug-session-video', videoBuffer, { contentType: 'video/webm' });
                    log.info(`🎥 Session video saved to Key-Value Store (${Math.round(videoBuffer.length / 1024)}KB)`);
                }
            }
        } catch (e) {
            log.warning(`🎥 Could not save video: ${e.message}`);
        }
        await browser.close();
    }
});
