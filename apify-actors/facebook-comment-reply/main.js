/**
 * Facebook Comment Actor - Scrape & Reply
 * 
 * Dual-mode Apify Actor:
 *   1. SCRAPE mode (no replyMessage): scrapes all comments from a post
 *   2. REPLY mode (with replyMessage): posts a comment/reply on a post
 * 
 * Uses Playwright with real cookies for reliable Facebook access.
 */

const { Actor, log } = require('apify');
const { chromium } = require('playwright');

let debugStepCounter = 0;

async function captureDebug(page, stepName, { saveHtml = false, fullPage = false } = {}) {
    debugStepCounter++;
    const prefix = `debug-${String(debugStepCounter).padStart(2, '0')}-${stepName}`;
    try {
        const buf = await page.screenshot({ fullPage, timeout: 10000 });
        await Actor.setValue(prefix, buf, { contentType: 'image/png' });
        log.info(`📸 Screenshot saved: ${prefix}.png`);
    } catch (e) {
        log.warning(`📸 Failed to capture screenshot: ${e.message}`);
    }
    if (saveHtml) {
        try {
            const html = await page.content();
            await Actor.setValue(`${prefix}-html`, html, { contentType: 'text/html' });
        } catch (e) { /* ignore */ }
    }
}

function randomDelay(minMs, maxMs) {
    return Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

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

async function setupBrowser(cookies, proxyConfigInput) {
    const launchOptions = {
        headless: false,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized',
        ],
    };

    let proxyConfiguration = null;
    if (proxyConfigInput?.useApifyProxy) {
        try {
            proxyConfiguration = await Actor.createProxyConfiguration({
                groups: proxyConfigInput.apifyProxyGroups || ['RESIDENTIAL'],
                countryCode: proxyConfigInput.apifyProxyCountry || 'IL',
            });
            log.info('🇮🇱 Israeli residential proxy configured');
        } catch (e) {
            log.warning(`⚠️ Could not set up proxy: ${e.message}. Proceeding without proxy.`);
        }
    }

    if (proxyConfiguration) {
        const sessionId = `fb_comment_${Date.now()}`;
        const proxyUrl = await proxyConfiguration.newUrl(sessionId);
        try {
            const parsed = new URL(proxyUrl);
            launchOptions.proxy = {
                server: `${parsed.protocol}//${parsed.hostname}:${parsed.port}`,
                username: decodeURIComponent(parsed.username),
                password: decodeURIComponent(parsed.password),
            };
            log.info(`🔒 Proxy: ${parsed.hostname}:${parsed.port}, user: ${parsed.username.substring(0, 30)}...`);
        } catch (e) {
            launchOptions.proxy = { server: proxyUrl };
            log.info(`🔒 Proxy (fallback): ${proxyUrl.replace(/:[^:]+@/, ':***@')}`);
        }
    } else if (proxyConfigInput?.proxyUrls?.length > 0) {
        launchOptions.proxy = { server: proxyConfigInput.proxyUrls[0] };
    }

    const browser = await chromium.launch(launchOptions);

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'he-IL',
        timezoneId: 'Asia/Jerusalem',
        extraHTTPHeaders: {
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
        },
    });

    // Comprehensive stealth - run BEFORE any navigation
    await context.addInitScript(() => {
        // Hide webdriver
        Object.defineProperty(navigator, 'webdriver', { get: () => false });

        // Override plugins to look like real Chrome
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' },
            ],
        });

        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['he-IL', 'he', 'en-US', 'en'],
        });

        // Remove automation indicators from chrome object
        const originalQuery = window.navigator.permissions?.query;
        if (originalQuery) {
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);
        }

        // Hide automation-related properties
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    });

    // Cookie injection
    log.info(`🍪 Setting ${cookies.length} cookies...`);
    const cookiesToSet = cookies.map(c => {
        const cookie = {
            name: c.name,
            value: c.value,
            domain: c.domain || '.facebook.com',
            path: c.path || '/',
            httpOnly: c.httpOnly !== undefined ? c.httpOnly : false,
            secure: c.secure !== undefined ? c.secure : true,
        };
        if (c.sameSite) {
            cookie.sameSite = c.sameSite;
        }
        if (c.expires && c.expires > 0) {
            cookie.expires = Math.floor(c.expires);
        }
        return cookie;
    });
    await context.addCookies(cookiesToSet);
    
    for (const c of cookiesToSet) {
        log.info(`🍪   ${c.name}: sameSite=${c.sameSite || 'default'}, expires=${c.expires || 'session'}`);
    }

    const page = await context.newPage();

    return { browser, context, page };
}

async function navigateAndVerifyLogin(page, postUrl) {
    // Navigate directly to the post URL (avoid triggering security on facebook.com homepage)
    log.info(`📄 Navigating directly to post: ${postUrl}`);
    await page.goto(postUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await sleep(randomDelay(5000, 8000));
    
    await captureDebug(page, 'initial-load', { saveHtml: true });

    // Check if we landed on a login page
    const currentUrl = page.url();
    log.info(`📍 Current URL: ${currentUrl}`);
    
    const loginForm = await page.$('input[name="email"]');
    const loginBtn = await page.$('[data-testid="royal_login_button"]');
    
    if (loginForm && loginBtn) {
        await captureDebug(page, 'login-required');
        
        // Try alternative: navigate to mobile facebook which is less strict
        log.info('⚠️ Login page detected, trying m.facebook.com...');
        const mobileUrl = postUrl.replace('www.facebook.com', 'm.facebook.com');
        await page.goto(mobileUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await sleep(randomDelay(4000, 6000));
        
        await captureDebug(page, 'mobile-attempt', { saveHtml: true });
        
        const mobileLogin = await page.$('input[name="email"]');
        if (mobileLogin) {
            await captureDebug(page, 'mobile-login-required');
            throw new Error('Not logged in - cookies may be expired (both www and m.facebook.com failed)');
        }
        log.info('✅ Mobile Facebook accepted cookies!');
    } else {
        log.info('✅ Logged in to Facebook');
    }

    // Close popups
    for (let i = 0; i < 3; i++) {
        try {
            const closeBtn = await page.$('[aria-label="Close"], [aria-label="סגירה"], [aria-label="Not Now"], [aria-label="לא עכשיו"]');
            if (closeBtn) {
                await closeBtn.click();
                await sleep(500);
            } else {
                break;
            }
        } catch (e) { break; }
    }
}

// ============================================================
// SCRAPE MODE - Extract all comments from a post
// ============================================================
async function scrapeComments(page, postUrl) {
    log.info('📜 SCRAPE MODE: Extracting comments...');

    // Scroll down to load comments
    for (let i = 0; i < 3; i++) {
        await page.evaluate(() => window.scrollBy(0, 500));
        await sleep(randomDelay(1000, 1500));
    }

    // Try to switch to "All comments" view
    try {
        const filterBtn = await page.$('div[role="button"] span:has-text("הרלוונטיות ביותר"), div[role="button"] span:has-text("Most relevant")');
        if (filterBtn) {
            await filterBtn.click();
            await sleep(1000);
            const allOption = await page.$('div[role="menuitem"]:has-text("כל התגובות"), div[role="menuitem"]:has-text("All comments")');
            if (allOption) {
                await allOption.click();
                log.info('✅ Switched to "All comments" view');
                await sleep(randomDelay(2000, 3000));
            } else {
                await page.keyboard.press('Escape');
                await sleep(300);
            }
        }
    } catch (e) {
        log.info('ℹ️ Could not switch comment filter');
    }

    // Click "View more comments" to load all
    for (let attempt = 0; attempt < 8; attempt++) {
        let clicked = false;
        try {
            const moreButtons = await page.$$('span:has-text("הצג"), span:has-text("View more"), span:has-text("תגובות נוספות"), span:has-text("תגובות קודמות"), span:has-text("previous comments")');
            for (const btn of moreButtons) {
                const text = await btn.textContent().catch(() => '');
                const visible = await btn.isVisible().catch(() => false);
                if (visible && (text.includes('הצג') || text.includes('View') || text.includes('תגובות') || text.includes('comments'))) {
                    await btn.click();
                    clicked = true;
                    log.info(`📜 Clicked: "${text.trim()}"`);
                    await sleep(randomDelay(2000, 3000));
                    break;
                }
            }
        } catch (e) { /* ignore */ }
        if (!clicked) break;
    }

    // Also expand any "View X replies" links
    try {
        const replyExpanders = await page.$$('span:has-text("תשובות"), span:has-text("replies"), span:has-text("תגובה")');
        for (const btn of replyExpanders) {
            const text = await btn.textContent().catch(() => '');
            const visible = await btn.isVisible().catch(() => false);
            if (visible && (text.match(/\d+\s*(תשובות|replies|תגובה)/) || text.match(/(View|הצג)\s+\d+/))) {
                try {
                    await btn.click();
                    await sleep(randomDelay(1500, 2500));
                } catch (e) { /* ignore */ }
            }
        }
    } catch (e) { /* ignore */ }

    // Scroll again
    for (let i = 0; i < 2; i++) {
        await page.evaluate(() => window.scrollBy(0, 400));
        await sleep(randomDelay(800, 1200));
    }

    await captureDebug(page, 'comments-loaded', { fullPage: true, saveHtml: true });

    // Strategy 1: Extract comments from embedded JSON/relay data
    const jsonComments = await page.evaluate(() => {
        const results = [];
        const seen = new Set();
        const html = document.documentElement.innerHTML;
        
        function decodeUnicode(str) {
            return str
                .replace(/\\u([0-9a-fA-F]{4})/g, (_, code) => String.fromCharCode(parseInt(code, 16)))
                .replace(/\\n/g, '\n')
                .replace(/\\\//g, '/');
        }
        
        // Pattern: find "body":{"text":"X"} then look AFTER it for "author":..:"name":"Y"
        // This matches Facebook's comment JSON structure: body comes before author
        const bodyRegex = /"body":\{"text":"((?:[^"\\]|\\.)*)"/g;
        let match;
        
        while ((match = bodyRegex.exec(html)) !== null) {
            const bodyEnd = match.index + match[0].length;
            // Look AFTER the body for author name (within 5000 chars)
            const afterHtml = html.substring(bodyEnd, Math.min(html.length, bodyEnd + 5000));
            // Also look before for created_time
            const beforeHtml = html.substring(Math.max(0, match.index - 2000), match.index);
            
            // Find author name that comes AFTER body in the same comment block
            const authorMatch = afterHtml.match(/"author":\{"__typename":"User"[^}]*?"name":"((?:[^"\\]|\\.)*)"/);
            // Also try: name before body (some structures)
            const authorBefore = beforeHtml.match(/"name":"((?:[^"\\]|\\.)*)"/g);
            
            const timeMatch = beforeHtml.match(/"created_time":(\d+)/) || afterHtml.match(/"created_time":(\d+)/);
            
            let name = '';
            if (authorMatch) {
                name = decodeUnicode(authorMatch[1]);
            } else if (authorBefore && authorBefore.length > 0) {
                // Take the LAST name before body (closest to the comment)
                const lastNameMatch = authorBefore[authorBefore.length - 1].match(/"name":"((?:[^"\\]|\\.)*)"/);
                if (lastNameMatch) name = decodeUnicode(lastNameMatch[1]);
            }
            
            if (!name) continue;
            
            const text = decodeUnicode(match[1]);
            if (text.length < 2) continue;
            
            const createdTime = timeMatch ? parseInt(timeMatch[1]) : 0;
            const key = `${name}::${text.substring(0, 80)}`;
            if (seen.has(key)) continue;
            seen.add(key);
            
            results.push({
                profileName: name,
                text,
                profileUrl: '',
                profilePicture: '',
                timestamp: createdTime ? new Date(createdTime * 1000).toISOString() : '',
                isReply: false,
            });
        }
        
        return results;
    });

    log.info(`📊 Strategy 1 (JSON extraction): found ${jsonComments.length} comments`);
    for (const c of jsonComments) {
        log.info(`  📝 JSON: ${c.profileName}: "${c.text.substring(0, 50)}"`);
    }

    // Strategy 2: DOM - only comments INSIDE the main post (first article). Never from "Other Posts".
    log.info('🔍 DOM strategy: only inside main post (no Other Posts)...');
    const domComments = await page.evaluate(() => {
        const results = [];
        const seen = new Set();
        const allArticles = document.querySelectorAll('div[role="article"]');
        let mainPost = null;
        for (const article of allArticles) {
            if (article.querySelector('[aria-label="Loading..."]')) continue;
            mainPost = article;
            break;
        }
        if (!mainPost) return results;
        // Only scan articles that are INSIDE the main post (nested comments), not siblings
        const insideMain = mainPost.querySelectorAll('div[role="article"]');
        const toScan = insideMain.length > 0 ? Array.from(insideMain) : [mainPost];
        for (const article of toScan) {
            if (article === mainPost && toScan.length > 1) continue;
            try {
                const links = article.querySelectorAll('a');
                let profileName = '';
                let profileUrl = '';
                
                for (const link of links) {
                    const href = link.href || '';
                    if (href.includes('facebook.com/') && 
                        !href.includes('/posts/') && !href.includes('/groups/') &&
                        !href.includes('/photos/') && !href.includes('/hashtag/') &&
                        !href.includes('/notifications') && !href.includes('/stories/')) {
                        const text = link.textContent?.trim();
                        if (text && text.length > 1 && text.length < 60 && 
                            !text.includes('http') && !text.match(/^\d+[hmdwשדחס]/)) {
                            profileName = text;
                            profileUrl = href;
                            break;
                        }
                    }
                }
                
                if (!profileName) continue;
                
                const textDivs = article.querySelectorAll('div[dir="auto"]');
                let commentText = '';
                const uiTexts = new Set(['Like', 'Reply', 'Share', 'אהבתי', 'הגב', 'הגבה', 'שתף',
                    'Write a comment…', 'כתיבת תגובה...', 'Admin', 'מנהל', 'Newest', 'חדש ביותר',
                    'All comments', 'כל התגובות', 'Most relevant', 'הרלוונטיות ביותר']);
                
                for (const td of textDivs) {
                    const t = td.textContent?.trim();
                    if (t && t.length > 2 && t !== profileName && !uiTexts.has(t) && t.length < 5000) {
                        commentText = t;
                        break;
                    }
                }
                
                if (!commentText) continue;
                
                const key = `${profileName}::${commentText.substring(0, 80)}`;
                if (seen.has(key)) continue;
                seen.add(key);
                
                results.push({ profileName, text: commentText, profileUrl, profilePicture: '', timestamp: '', isReply: false });
            } catch (e) { /* skip */ }
        }
        
        return results;
    });
    
    log.info(`📊 Strategy 2 (DOM): found ${domComments.length} comments`);
    for (const c of domComments) {
        log.info(`  📝 DOM: ${c.profileName}: "${c.text.substring(0, 50)}"`);
    }

    // Merge results (deduplicate by name+text key)
    const allSeen = new Set();
    const comments = [];
    for (const c of [...jsonComments, ...domComments]) {
        const key = `${c.profileName}::${c.text.substring(0, 80)}`;
        if (!allSeen.has(key)) {
            allSeen.add(key);
            comments.push(c);
        }
    }

    // Add metadata and generate unique IDs
    const crypto = require('crypto');
    const enrichedComments = comments.map((c, i) => {
        const hash = crypto.createHash('md5')
            .update(`${c.profileName}:${c.text}:${i}`)
            .digest('hex')
            .substring(0, 20);
        return {
            ...c,
            id: `pw_${hash}`,
            postUrl: postUrl,
            scrapedAt: new Date().toISOString(),
            index: i,
        };
    });

    return enrichedComments;
}

// ============================================================
// REPLY MODE - Post a comment on a post
// ============================================================
async function postReply(page, replyMessage, commentId) {
    log.info('💬 REPLY MODE: Posting comment...');
    log.info(`💬 Reply text: "${replyMessage.substring(0, 80)}..."`);
    log.info(`💬 Comment ID: ${commentId || 'none (top-level comment)'}`);

    // Wait for page to fully load
    log.info('⏳ Waiting for page to fully render...');
    await sleep(randomDelay(3000, 5000));

    // Scroll down gradually to load the comments section
    for (let i = 0; i < 5; i++) {
        await page.evaluate(() => window.scrollBy(0, 400));
        await sleep(randomDelay(800, 1200));
    }

    await captureDebug(page, 'reply-page-loaded', { fullPage: true });

    // Try to load more comments if needed
    try {
        const moreComments = await page.$('span:has-text("תגובות נוספות"), span:has-text("more comments"), span:has-text("View more")');
        if (moreComments) {
            await moreComments.click();
            await sleep(randomDelay(2000, 3000));
        }
    } catch (e) { /* ignore */ }

    // If commentId is provided, try to find and click the reply button for that specific comment
    if (commentId) {
        log.info(`🎯 Looking for reply button for comment: ${commentId}`);
        try {
            const replyButtons = await page.$$('div[role="button"]');
            let clickedReply = false;
            for (const btn of replyButtons) {
                const text = await btn.textContent().catch(() => '');
                const trimmed = text.trim();
                if (trimmed === 'הגב' || trimmed === 'הגבה' || trimmed === 'Reply') {
                    const visible = await btn.isVisible().catch(() => false);
                    if (visible) {
                        await btn.click();
                        clickedReply = true;
                        log.info(`✅ Clicked reply button: "${trimmed}"`);
                        await sleep(randomDelay(1500, 2500));
                        break;
                    }
                }
            }
            if (!clickedReply) {
                const altReplyBtns = await page.$$('[aria-label="Reply"], [aria-label="הגב"], [aria-label="הגבה"]');
                for (const btn of altReplyBtns) {
                    const visible = await btn.isVisible().catch(() => false);
                    if (visible) {
                        await btn.click();
                        clickedReply = true;
                        log.info('✅ Clicked reply button via aria-label');
                        await sleep(randomDelay(1500, 2500));
                        break;
                    }
                }
            }
            if (!clickedReply) {
                log.info('ℹ️ No specific reply button found, will post as top-level comment');
            }
        } catch (e) {
            log.warning(`⚠️ Error finding reply button: ${e.message}`);
        }
    }

    await captureDebug(page, 'before-editor-search');

    // Step 1: Try to find an already-visible comment editor
    log.info('🔍 Step 1: Looking for visible comment editor...');
    let editor = await findVisibleEditor(page);

    // Step 2: If no editor, try clicking on comment placeholder areas
    if (!editor) {
        log.info('🔍 Step 2: Trying to activate comment input by clicking placeholders...');
        editor = await activateCommentInput(page);
    }

    // Step 3: If still no editor, try scrolling to the comment form area
    if (!editor) {
        log.info('🔍 Step 3: Scrolling to find comment area...');
        // Scroll back up to find comment form near post
        await page.evaluate(() => window.scrollTo(0, 0));
        await sleep(1000);
        // Scroll down slowly looking for comment form
        for (let i = 0; i < 8; i++) {
            await page.evaluate(() => window.scrollBy(0, 300));
            await sleep(800);
            editor = await findVisibleEditor(page);
            if (editor) {
                log.info(`📝 Found editor after scrolling (iteration ${i})`);
                break;
            }
        }
    }

    // Step 4: Try clicking on any form-like element
    if (!editor) {
        log.info('🔍 Step 4: Looking for form elements...');
        try {
            const forms = await page.$$('form');
            for (const form of forms) {
                const visible = await form.isVisible().catch(() => false);
                if (!visible) continue;
                const formHtml = await form.evaluate(el => el.innerHTML.substring(0, 200)).catch(() => '');
                log.info(`  📋 Form found: ${formHtml.substring(0, 100)}`);
                // Click inside the form to activate it
                await form.click().catch(() => {});
                await sleep(1500);
                editor = await findVisibleEditor(page);
                if (editor) {
                    log.info('📝 Found editor after clicking form');
                    break;
                }
            }
        } catch (e) { /* ignore */ }
    }

    // Step 5: Try using Tab key to navigate to comment input
    if (!editor) {
        log.info('🔍 Step 5: Trying Tab navigation...');
        for (let i = 0; i < 15; i++) {
            await page.keyboard.press('Tab');
            await sleep(300);
            const focused = await page.evaluate(() => {
                const el = document.activeElement;
                return {
                    tag: el?.tagName,
                    editable: el?.contentEditable === 'true',
                    role: el?.getAttribute('role'),
                    label: el?.getAttribute('aria-label') || '',
                };
            });
            if (focused.editable || focused.role === 'textbox') {
                log.info(`📝 Found editable element via Tab: tag=${focused.tag}, label=${focused.label}`);
                editor = await page.$(':focus');
                break;
            }
        }
    }

    if (!editor) {
        // Capture extensive debug info
        await captureDebug(page, 'no-editor-found', { saveHtml: true, fullPage: true });
        
        // Log all contenteditable elements on page for debugging
        const editableInfo = await page.evaluate(() => {
            const editables = document.querySelectorAll('[contenteditable="true"]');
            return Array.from(editables).map(el => ({
                tag: el.tagName,
                visible: el.offsetParent !== null,
                width: el.offsetWidth,
                height: el.offsetHeight,
                label: el.getAttribute('aria-label') || '',
                role: el.getAttribute('role') || '',
                text: el.textContent?.substring(0, 50) || '',
            }));
        });
        log.info(`📊 All contenteditable elements on page: ${JSON.stringify(editableInfo, null, 2)}`);
        
        // Also log all role=textbox elements
        const textboxInfo = await page.evaluate(() => {
            const textboxes = document.querySelectorAll('[role="textbox"]');
            return Array.from(textboxes).map(el => ({
                tag: el.tagName,
                visible: el.offsetParent !== null,
                width: el.offsetWidth,
                height: el.offsetHeight,
                label: el.getAttribute('aria-label') || '',
                editable: el.contentEditable,
            }));
        });
        log.info(`📊 All textbox elements on page: ${JSON.stringify(textboxInfo, null, 2)}`);
        
        throw new Error('Could not find comment editor on page');
    }

    await captureDebug(page, 'editor-found');

    // Type the reply
    log.info(`⌨️ Typing reply (${replyMessage.length} chars)...`);
    await humanTypeIntoEditor(page, editor, replyMessage);
    await sleep(randomDelay(500, 1000));
    await captureDebug(page, 'reply-typed');

    // Submit
    log.info('📤 Submitting reply (Enter)...');
    await page.keyboard.press('Enter');
    await sleep(randomDelay(4000, 6000));
    await captureDebug(page, 'reply-submitted');

    // Verify the reply appeared
    const pageContent = await page.content();
    const shortReply = replyMessage.substring(0, 30);
    if (pageContent.includes(shortReply)) {
        log.info('✅ Reply text confirmed on page!');
    } else {
        log.warning('⚠️ Reply text not found on page after submit - may not have been submitted');
        await captureDebug(page, 'reply-not-confirmed', { saveHtml: true });
    }

    return { success: true };
}

async function findVisibleEditor(page) {
    const editorSelectors = [
        'div[contenteditable="true"][aria-label*="תגובה"]',
        'div[contenteditable="true"][aria-label*="comment"]',
        'div[contenteditable="true"][aria-label*="Comment"]',
        'div[contenteditable="true"][aria-label*="Write"]',
        'div[contenteditable="true"][aria-label*="Reply"]',
        'div[contenteditable="true"][aria-label*="הגב"]',
        'div[contenteditable="true"][aria-label*="כתיבת"]',
        'div[contenteditable="true"][role="textbox"]',
        'p[contenteditable="true"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[contenteditable="true"]',
    ];

    for (const selector of editorSelectors) {
        try {
            const elements = await page.$$(selector);
            for (const el of elements) {
                const visible = await el.isVisible().catch(() => false);
                if (!visible) continue;
                const box = await el.boundingBox().catch(() => null);
                if (box && box.width > 40 && box.height > 8) {
                    const label = await el.getAttribute('aria-label').catch(() => '');
                    log.info(`📝 Found editor: selector="${selector}", label="${label}", size=${Math.round(box.width)}x${Math.round(box.height)}`);
                    return el;
                }
            }
        } catch (e) { /* try next */ }
    }
    return null;
}

async function activateCommentInput(page) {
    // Try clicking on various placeholder/input-like elements
    const placeholderSelectors = [
        '[aria-label*="Write a comment"]',
        '[aria-label*="כתיבת תגובה"]',
        '[aria-label*="Write a reply"]',
        '[aria-label*="כתיבת תשובה"]',
        '[aria-label*="תגובה"]',
        '[placeholder*="comment"]',
        '[placeholder*="תגובה"]',
        'div[role="textbox"]',
        'div[data-testid="UFI2CommentBorderlessInput/Root"]',
    ];

    for (const selector of placeholderSelectors) {
        try {
            const elements = await page.$$(selector);
            for (const el of elements) {
                const visible = await el.isVisible().catch(() => false);
                if (!visible) continue;
                
                log.info(`🖱️ Clicking placeholder: ${selector}`);
                await el.click();
                await sleep(randomDelay(1500, 2500));
                
                // After clicking, look for an activated editor
                const editor = await findVisibleEditor(page);
                if (editor) {
                    log.info('📝 Editor activated after clicking placeholder');
                    return editor;
                }
            }
        } catch (e) { /* try next */ }
    }
    
    // Also try: look for the comment input image (avatar) area and click next to it
    try {
        const avatarImgs = await page.$$('image, img[alt]');
        // Not reliable, skip
    } catch (e) { /* ignore */ }

    return null;
}

// ============================================================
// Main
// ============================================================
Actor.main(async () => {
    log.info('🚀 Facebook Comment Actor v2 started');

    const input = await Actor.getInput();
    if (!input) throw new Error('No input provided');

    const { postUrl, commentId, replyMessage, cookies, proxyConfiguration, mode } = input;

    if (!postUrl) throw new Error('postUrl is required');
    if (!cookies || cookies.length === 0) throw new Error('cookies are required');

    const actorMode = mode || (replyMessage ? 'reply' : 'scrape');
    log.info(`📋 Mode: ${actorMode}`);

    let browser = null;

    try {
        const setup = await setupBrowser(cookies, proxyConfiguration);
        browser = setup.browser;
        const page = setup.page;

        await navigateAndVerifyLogin(page, postUrl);
        await captureDebug(page, 'page-loaded', { saveHtml: actorMode === 'scrape' });

        if (actorMode === 'scrape') {
            const comments = await scrapeComments(page, postUrl);
            log.info(`📊 Total comments found: ${comments.length}`);
            for (const comment of comments) {
                log.info(`  💬 ${comment.profileName}: "${comment.text.substring(0, 60)}..."`);
                await Actor.pushData(comment);
            }
            log.info(`📊 Pushed ${comments.length} comments to dataset`);
        } else {
            if (!replyMessage) throw new Error('replyMessage is required for reply mode');
            await postReply(page, replyMessage, commentId);
            await Actor.pushData({ success: true, mode: 'reply' });
            log.info('✅ Comment reply posted successfully!');
        }

    } catch (error) {
        log.error(`❌ Error: ${error.message}`);
        await Actor.pushData({ success: false, error: error.message, mode: actorMode });
    } finally {
        if (browser) {
            await browser.close();
        }
    }

    log.info('🏁 Actor finished');
});
