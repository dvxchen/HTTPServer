/**
 * Auto-generated test runner based on server.csv
 *
 * This script reads the CSV steps and executes them in a real browser using Playwright.
 *
 * Recognized step patterns in server.csv:
 * 1) "Launch Chrome and navigate to <url> ; maximize the browser window."
 * 2) "Enter 'Some text' in the 输入消息框"
 * 3) "Click 发送"
 * 4) "wait N seconds"
 * 5) "读取第一个文本框内容" (Read the first text box content)
 * 6) "读取 <selector> 的内容"
 * 7) "读取第一个 class 为 <classes> 元素的内容"
 *
 * How to run:
 *   1) npm i -D playwright
 *   2) npx playwright install
 *   3) node test.js
 *
 * Notes:
 * - The script attempts to launch the installed Chrome (channel: 'chrome') first,
 *   and falls back to the bundled Chromium if Chrome isn’t available.
 * - The script uses heuristics to find the first visible text input/textarea/contenteditable
 *   when entering text and reading value. Adjust selectors if your app’s DOM differs.
 */

const fs = require('fs');
const path = require('path');
const playwright = require('playwright');

const LOG_PATH = path.resolve(__dirname, 'log.json');
function initLog() {
    try {
        // Truncate the log file on every run
        fs.writeFileSync(LOG_PATH, '');
    } catch (e) {
        console.error('Failed to init log:', e);
    }
}
function logEvent(event) {
    const entry = Object.assign({ time: new Date().toISOString() }, event);
    try {
        // NDJSON: one JSON object per line
        fs.appendFileSync(LOG_PATH, JSON.stringify(entry) + '\n');
    } catch (e) {
        console.error('Failed to write log:', e);
    }
}

function getHeadlessSetting() {
    try {
        const settingsPath = path.resolve(__dirname, 'Settings.json');
        if (fs.existsSync(settingsPath)) {
            const raw = fs.readFileSync(settingsPath, 'utf8');
            const cfg = JSON.parse(raw);
            const v = cfg && cfg.HEADLESS;
            if (typeof v === 'boolean') return v;
            if (typeof v === 'string') {
                const s = v.trim().toLowerCase();
                if (['true', '1', 'yes', 'y', 'on'].includes(s)) return true;
                if (['false', '0', 'no', 'n', 'off'].includes(s)) return false;
            }
            if (typeof v === 'number') return v !== 0;
        }
    } catch (e) {
        console.warn('Failed to read Settings.json HEADLESS:', e.message);
    }
    return false;
}

function parseCsv(filePath) {
    const raw = fs.readFileSync(filePath, 'utf8');
    const lines = raw
        .split(/\r?\n/)
        .map(l => l.trim())
        .filter(l => l.length > 0);

    const rows = [];
    for (const line of lines) {
        // Very simple CSV split by comma. We only use the first cell (Action).
        const parts = line.split(',');
        const action = (parts[0] || '').trim();
        const data = (parts[1] || '').trim();
        const expected = (parts[2] || '').trim();
        rows.push({ action, data, expected });
    }

    // Remove header row if present
    const filtered = rows.filter((r, idx) => {
        if (idx === 0 && r.action.toLowerCase() === 'action') return false;
        return true;
    });

    return filtered;
}

async function launchBrowser() {
    // Try Chrome first, fall back to bundled Chromium; headless is read from Settings.json
    const headless = getHeadlessSetting();
    try {
        return await playwright.chromium.launch({ headless, channel: 'chrome' });
    } catch (e) {
        console.warn('Chrome channel launch failed, falling back to bundled Chromium:', e.message);
        return await playwright.chromium.launch({ headless });
    }
}

async function fillFirstTextInput(page, text) {
    const locator = page.locator('input:not([type]), input[type="text"], textarea, [contenteditable="true"]');
    const first = locator.first();
    await first.waitFor({ state: 'visible', timeout: 10000 });

    const tagName = await first.evaluate(el => el.tagName ? el.tagName.toLowerCase() : '');
    const isContentEditable = await first.evaluate(el => el.getAttribute && el.getAttribute('contenteditable') === 'true');

    if (tagName === 'input' || tagName === 'textarea') {
        await first.fill(text);
    } else if (isContentEditable) {
        await first.click();
        await page.keyboard.type(text);
    } else {
        // Fallback attempt
        try {
            await first.fill(text);
        } catch {
            await first.click();
            await page.keyboard.type(text);
        }
    }
}

async function readFirstTextInputValue(page) {
    const locator = page.locator('input:not([type]), input[type="text"], textarea, [contenteditable="true"]');
    const first = locator.first();
    await first.waitFor({ state: 'visible', timeout: 10000 });
    const value = await first.evaluate(el => {
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea') return el.value || '';
        if (el.getAttribute && el.getAttribute('contenteditable') === 'true') return el.textContent || '';
        return '';
    });
    return value;
}

async function readElementText(page, selector) {
    const loc = page.locator(selector).first();
    await loc.waitFor({ state: 'visible', timeout: 10000 });
    const text = await loc.evaluate(el => {
        if (typeof el.innerText === 'string') return el.innerText;
        return el.textContent || '';
    });
    return (text || '').trim();
}

function buildClassSelectorFromText(text) {
    if (!text) return '';
    let t = text.trim()
        .replace(/[·。．\.、，,！!？?]+$/g, '')
        .trim();
    const parts = t.split(/\s+/).filter(Boolean);
    const classes = parts
        .map(p => p.replace(/[·。．\.、，,！!？?]/g, '').replace(/^\./, ''))
        .filter(Boolean);
    if (!classes.length) return '';
    return classes.map(c => `.${c}`).join('');
}

async function clickByText(page, text) {
    // Try role-based button
    try {
        await page.getByRole('button', { name: new RegExp(text, 'i') }).click({ timeout: 3000 });
        return;
    } catch { }

    // Try generic text selector
    try {
        await page.locator(`text=${text}`).first().click({ timeout: 3000 });
        return;
    } catch { }

    // Try common button patterns
    try {
        await page.locator(`button:has-text("${text}")`).first().click({ timeout: 3000 });
        return;
    } catch { }

    try {
        await page.locator(`[role="button"]:has-text("${text}")`).first().click({ timeout: 3000 });
        return;
    } catch { }

    console.warn(`Could not find a clickable element with text "${text}".`);
}

async function runSteps(steps) {
    const browser = await launchBrowser();

    // Use a large viewport to simulate "maximize"
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();

    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const action = (step.action || '').trim();

        if (!action) continue;
        console.log(`Step ${i + 1}: ${action}`);
        logEvent({ type: 'step', stage: 'start', index: i + 1, action });

        // 1) Launch Chrome and navigate to <url> ; maximize the browser window.
        if (/^Launch Chrome and navigate to\s+/i.test(action)) {
            const urlMatch = action.match(/https?:\/\/[^\s;]+/i);
            const url = urlMatch ? urlMatch[0] : (step.data || 'http://127.0.0.1:5000/');
            await page.goto(url, { waitUntil: 'load', timeout: 30000 });

            // Best-effort "maximize" the window size via window.resize (may be blocked by some browsers)
            try {
                await page.evaluate(() => {
                    try {
                        window.moveTo(0, 0);
                        window.resizeTo(screen.availWidth, screen.availHeight);
                    } catch (e) {
                        // Ignored
                    }
                });
            } catch { }
            logEvent({ type: 'navigate', stage: 'success', index: i + 1, action, url });
            continue;
        }

        // 2) Enter 'Hello World' in the 输入消息框
        if (/^Enter\s+['"](.*)['"]\s+in\s+.*输入消息框/i.test(action)) {
            const m = action.match(/^Enter\s+['"](.*)['"]\s+in\s+/i);
            let text = m ? m[1] : '';
            if (!text) text = step.data || 'Hello World';
            await fillFirstTextInput(page, text);
            logEvent({ type: 'input', stage: 'success', index: i + 1, action, text });
            continue;
        }

        // 3) Click 发送 (supports Chinese or English "Send")
        if (/^Click\s+.*发送/i.test(action) || /点击\s*发送/.test(action) || /^Click\s+Send/i.test(action)) {
            await clickByText(page, '发送');
            logEvent({ type: 'click', stage: 'success', index: i + 1, action, targetText: '发送' });
            continue;
        }

        // 4) wait N seconds
        if (/^wait\s+(\d+)\s*seconds?/i.test(action)) {
            const m = action.match(/^wait\s+(\d+)\s*seconds?/i);
            const seconds = m ? parseInt(m[1], 10) : 5;
            console.log(`Waiting ${seconds} seconds...`);
            await page.waitForTimeout(seconds * 1000);
            logEvent({ type: 'wait', stage: 'success', index: i + 1, action, seconds });
            continue;
        }

        // 5) 读取第一个文本框内容
        if (/读取.*第一个.*文本框.*内容/.test(action)) {
            const value = await readFirstTextInputValue(page);
            console.log(`First textbox content: ${value}`);
            logEvent({ type: 'read', stage: 'success', index: i + 1, action, target: 'firstTextBox', value });
            continue;
        }

        // 5b) 读取第一个 class 为 <classes> 元素的内容
        if (/^读取第一个[·\s]*class为(.+?)元素的内容(?:[·。．\.、，,！!？?]*)?$/i.test(action)) {
            const m = action.match(/^读取第一个[·\s]*class为(.+?)元素的内容/i);
            const classText = m ? m[1] : '';
            const selector = buildClassSelectorFromText(classText);
            if (selector) {
                const value = await readElementText(page, selector);
                console.log(`Content of first element ${selector}: ${value}`);
                logEvent({ type: 'read', stage: 'success', index: i + 1, action, selector, value });
            } else {
                console.warn('Could not parse class selector from action.');
            }
            continue;
        }

        // 5c) 读取 <selector> 的内容
        if (/^读取\s+(.+?)\s+的内容(?:[。．\.·、，,！!？?]*)?$/i.test(action)) {
            const m = action.match(/^读取\s+(.+?)\s+的内容/);
            const selector = m ? m[1].trim() : '';
            if (selector) {
                const value = await readElementText(page, selector);
                console.log(`Content of "${selector}": ${value}`);
                logEvent({ type: 'read', stage: 'success', index: i + 1, action, selector, value });
            } else {
                console.warn('Selector not found in action.');
            }
            continue;
        }

        console.warn(`Unrecognized step: "${action}". Skipping.`);
        logEvent({ type: 'step', stage: 'skipped', index: i + 1, action, reason: 'Unrecognized step' });
    }

    await page.close();
    await context.close();
    await browser.close();
}

(async () => {
    const csvPath = path.resolve(__dirname, 'server.csv');
    if (!fs.existsSync(csvPath)) {
        console.error(`CSV not found at: ${csvPath}`);
        process.exit(1);
    }

    initLog();
    const steps = parseCsv(csvPath);
    const headless = getHeadlessSetting();
    logEvent({ type: 'run', stage: 'init', stepsCount: steps.length, headless });
    if (!steps.length) {
        console.error('No steps found in CSV.');
        process.exit(1);
    }

    await runSteps(steps);
})().catch(err => {
    console.error(err);
    process.exit(1);
});