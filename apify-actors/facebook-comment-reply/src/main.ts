/**
 * Facebook Comment Reply Actor
 * 
 * This Apify Actor replies to comments on Facebook posts.
 * Uses Playwright for browser automation with anti-detection measures.
 */

import { Actor, log } from 'apify';
import { chromium, Browser, Page, BrowserContext } from 'playwright';

interface Input {
    postUrl: string;
    commentId?: string;
    replyMessage: string;
    cookies: Array<{
        name: string;
        value: string;
        domain: string;
        path?: string;
    }>;
    proxyConfiguration?: {
        useApifyProxy?: boolean;
        proxyUrls?: string[];
    };
}

interface Output {
    success: boolean;
    commentId?: string;
    error?: string;
    screenshotUrl?: string;
}

// Random delay to appear more human-like
const randomDelay = (min: number, max: number): Promise<void> => {
    const delay = Math.floor(Math.random() * (max - min + 1)) + min;
    return new Promise(resolve => setTimeout(resolve, delay));
};

// Type text like a human (random delays between keystrokes)
const typeHuman = async (page: Page, selector: string, text: string): Promise<void> => {
    await page.click(selector);
    for (const char of text) {
        await page.keyboard.type(char);
        await randomDelay(50, 150);
    }
};

Actor.main(async () => {
    log.info('🚀 Facebook Comment Reply Actor started');

    const input = await Actor.getInput() as Input;

    if (!input) {
        throw new Error('No input provided');
    }

    const { postUrl, commentId, replyMessage, cookies, proxyConfiguration } = input;

    // Validate input
    if (!postUrl) {
        throw new Error('postUrl is required');
    }
    if (!replyMessage) {
        throw new Error('replyMessage is required');
    }
    if (!cookies || cookies.length === 0) {
        throw new Error('Facebook cookies are required for authentication');
    }

    let browser: Browser | null = null;
    let context: BrowserContext | null = null;
    let page: Page | null = null;

    const output: Output = {
        success: false,
    };

    try {
        log.info('🌐 Launching browser...');

        // Browser launch options
        const launchOptions: any = {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ],
        };

        // Add proxy if configured
        if (proxyConfiguration?.proxyUrls && proxyConfiguration.proxyUrls.length > 0) {
            const proxyUrl = proxyConfiguration.proxyUrls[0];
            launchOptions.proxy = { server: proxyUrl };
            log.info(`🔒 Using proxy: ${proxyUrl}`);
        }

        browser = await chromium.launch(launchOptions);

        // Create context with realistic settings
        context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport: { width: 1280, height: 720 },
            locale: 'he-IL',
            timezoneId: 'Asia/Jerusalem',
        });

        // Set cookies
        log.info('🍪 Setting Facebook cookies...');
        await context.addCookies(cookies.map(c => ({
            name: c.name,
            value: c.value,
            domain: c.domain || '.facebook.com',
            path: c.path || '/',
        })));

        page = await context.newPage();

        // Navigate to the post
        log.info(`📄 Navigating to post: ${postUrl}`);
        await page.goto(postUrl, { waitUntil: 'networkidle', timeout: 60000 });

        // Wait for page to load
        await randomDelay(2000, 4000);

        // Check if we're logged in
        const isLoggedIn = await page.$('input[name="email"]') === null;
        if (!isLoggedIn) {
            throw new Error('Not logged in - cookies may be expired');
        }

        log.info('✅ Logged in successfully');

        // Scroll to comments section
        log.info('📜 Scrolling to comments...');
        await page.evaluate(() => {
            window.scrollBy(0, 500);
        });
        await randomDelay(1000, 2000);

        // Find the comment reply box or comment input
        // Note: Facebook's DOM changes frequently, selectors may need updates
        const commentBoxSelector = 'div[contenteditable="true"][role="textbox"]';
        
        log.info('🔍 Looking for comment input...');
        
        if (commentId) {
            // Find specific comment and click reply
            log.info(`🎯 Looking for comment ID: ${commentId}`);
            
            // Try to find the reply button for the specific comment
            // This is a simplified approach - actual implementation would need
            // to navigate the complex Facebook DOM structure
            const replyButton = await page.$(`[data-commentid="${commentId}"] [aria-label*="Reply"], [data-commentid="${commentId}"] [aria-label*="הגב"]`);
            
            if (replyButton) {
                await replyButton.click();
                await randomDelay(500, 1000);
            }
        }

        // Wait for comment input to appear
        await page.waitForSelector(commentBoxSelector, { timeout: 10000 });

        // Find the last (most relevant) comment box
        const commentBoxes = await page.$$(commentBoxSelector);
        if (commentBoxes.length === 0) {
            throw new Error('Could not find comment input box');
        }

        const targetBox = commentBoxes[commentBoxes.length - 1];

        // Type the reply
        log.info('⌨️ Typing reply...');
        await targetBox.click();
        await randomDelay(300, 600);

        // Type character by character for human-like behavior
        for (const char of replyMessage) {
            await page.keyboard.type(char);
            await randomDelay(30, 80);
        }

        await randomDelay(500, 1000);

        // Submit the reply (Enter key or find submit button)
        log.info('📤 Submitting reply...');
        await page.keyboard.press('Enter');
        
        // Wait for submission
        await randomDelay(2000, 4000);

        // Take screenshot for verification
        const screenshot = await page.screenshot();
        const screenshotKey = `screenshot_${Date.now()}.png`;
        await Actor.setValue(screenshotKey, screenshot, { contentType: 'image/png' });

        output.success = true;
        output.screenshotUrl = screenshotKey;
        log.info('✅ Reply posted successfully!');

    } catch (error: any) {
        log.error(`❌ Error: ${error.message}`);
        output.success = false;
        output.error = error.message;

        // Take error screenshot
        if (page) {
            try {
                const screenshot = await page.screenshot();
                const screenshotKey = `error_screenshot_${Date.now()}.png`;
                await Actor.setValue(screenshotKey, screenshot, { contentType: 'image/png' });
                output.screenshotUrl = screenshotKey;
            } catch (e) {
                log.warning('Could not take error screenshot');
            }
        }
    } finally {
        // Cleanup
        if (browser) {
            await browser.close();
        }
    }

    // Save output
    await Actor.pushData(output);
    log.info('📊 Output saved');
    log.info(`Result: ${output.success ? 'SUCCESS' : 'FAILED'}`);
});
