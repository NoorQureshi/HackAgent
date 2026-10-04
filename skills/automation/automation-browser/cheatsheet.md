# Browser & desktop automation cheatsheet

> Companion to `SKILL.md`. Covers agent-browser CLI, the Playwright Node API, pentest patterns,
> and the OpenReverse desktop-automation lane. Use only against in-scope targets.

## agent-browser CLI

### Navigation & lifecycle
```bash
agent-browser open "https://target.com/login"
agent-browser wait --load networkidle
agent-browser close                     # mandatory — leaked processes hang later runs
```

### Snapshot (always before acting)
```bash
agent-browser snapshot                  # full accessibility tree (debug)
agent-browser snapshot -i               # interactive elements only → @e1, @e2... (preferred)
```

### Interaction
```bash
agent-browser click @e1
agent-browser fill @e2 "admin"          # sets value directly
agent-browser type @e2 "password123"    # per-character events — use when JS listens on input
agent-browser press Enter|Tab|Escape
agent-browser scroll down 500
```

### Read state
```bash
agent-browser get text @e1
agent-browser get title
agent-browser get url
```

### Waiting
```bash
agent-browser wait @e1                  # element appears
agent-browser wait 2000                 # fixed ms — last resort
agent-browser wait --load networkidle   # network quiet
agent-browser wait --load domcontentloaded
```

## Pentest patterns

### Automated login
```bash
agent-browser open "https://target.com/login"
agent-browser snapshot -i
agent-browser fill @user "admin"
agent-browser type @pass "password123"
agent-browser click @submit
agent-browser wait --load networkidle
agent-browser get url                   # confirm the authenticated landing page
```

### XSS payload through the UI
```bash
agent-browser open "https://target.com/search"
agent-browser snapshot -i
agent-browser fill @q "<script>alert(1)</script>"
agent-browser click @go
agent-browser wait --load networkidle
agent-browser snapshot                  # is the payload reflected unencoded?
```

### Batch form submission (payload loop)
```bash
for p in "' OR 1=1--" "<img src=x onerror=alert(1)>" "{{7*7}}"; do
  agent-browser open "https://target.com/form"
  agent-browser snapshot -i
  agent-browser fill @input "$p"
  agent-browser click @submit
  agent-browser wait --load networkidle
  agent-browser snapshot
done
agent-browser close
```

## Playwright Node API

### Base template (Burp-proxy-ready)
```javascript
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    proxy: { server: 'http://127.0.0.1:8080' },   // through Burp
  });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: 'Mozilla/5.0 ...',
  });
  const page = await context.newPage();
  await page.goto('https://target.com');
  // ...
  await browser.close();
})();
```

### Selectors
```javascript
await page.click('#login-btn');                       // CSS
await page.fill('input[name="username"]', 'admin');
await page.click('text=Submit');                      // text
await page.click('button:has-text("Login")');
await page.click('xpath=//button[@type="submit"]');   // XPath
await page.click('form >> input[type="submit"]');     // chained
```

### Storage & evidence extraction
```javascript
const cookies = await context.cookies();
console.log(JSON.stringify(cookies, null, 2));
const storage = await page.evaluate(() => JSON.stringify(localStorage));
await page.screenshot({ path: 'evidence.png', fullPage: true });
```

### Network interception
```javascript
// log API calls
await page.route('**/api/**', route => {
  console.log('API call:', route.request().url());
  route.continue();
});

// modify a request
await page.route('**/api/auth', route => {
  route.continue({
    headers: { ...route.request().headers(), 'X-Admin': 'true' },
  });
});

// tamper with a response (test client-side authorization)
await page.route('**/api/user', async route => {
  const response = await route.fetch();
  const json = await response.json();
  json.role = 'admin';
  route.fulfill({ response, json });
});
```

### Waits & assertions
```javascript
await page.waitForSelector('#result');
await page.waitForSelector('.error', { state: 'visible' });

const [response] = await Promise.all([
  page.waitForResponse('**/api/login'),
  page.click('#login-btn'),
]);
console.log(response.status(), await response.json());

await Promise.all([
  page.waitForNavigation(),
  page.click('a[href="/admin"]'),
]);
```

## OpenReverse (Windows desktop automation)

For desktop GUI targets instead of web pages. Two interaction modes plus a network lane:

| Mode | Use when | Backing |
|------|----------|---------|
| UIA | standard Windows controls (buttons, edits, lists) | Windows UI Automation API |
| CUA | custom-rendered GUIs (IDA disassembly view, drawn canvases) | vision + mouse/keyboard |

| Network lane | Use when |
|--------------|----------|
| proxy | the app can be pointed at a proxy (preferred) |
| local | the app ignores proxy settings — capture locally |

### Install
```bash
git clone https://github.com/zhexulong/openreverse.git
cd openreverse && npm install
npm run init:agents -- --target=all /path/to/project
npm run install:cua-runtime && npm run doctor:cua-runtime   # optional: vision mode
npm run install:mitmproxy  && npm run doctor:network        # optional: network lane
```

### UIA commands
```bash
openreverse uia launch "C:\Tools\x64dbg\x64dbg.exe"
openreverse uia tree                      # window control tree
openreverse uia click "Button:Open"
openreverse uia fill "Edit:FilePath" "C:\sample.exe"
openreverse uia menu "File > Open"
openreverse uia get-text "Edit:Output"
```

### CUA commands
```bash
openreverse cua screenshot                # confirm coordinates first — DPI mismatches shift clicks
openreverse cua click 500 300
openreverse cua dblclick 500 300
openreverse cua type "search string"
openreverse cua key "ctrl+g"              # IDA: go to address
openreverse cua key "F5"                  # IDA: decompile
openreverse cua key "F9"                  # x64dbg: run
```

### Network observation
```bash
openreverse network start --mode proxy --port 8888
openreverse network start --mode local --filter "target.exe"
openreverse network list
openreverse network export har output.har
openreverse network stop
```

### Example: batch-debug with x64dbg
```text
1. openreverse uia launch "x64dbg.exe"
2. openreverse cua key "F3"                        # open file dialog
3. openreverse uia fill "Edit:FileName" "target.exe"
4. openreverse uia click "Button:Open"
5. openreverse cua key "ctrl+g" → type "0x401000"  # go to address
6. openreverse cua key "F2"                        # breakpoint
7. openreverse cua key "F9"                        # run
8. openreverse cua screenshot                      # capture state as evidence
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| agent-browser unresponsive | leaked process | `close`, then `open` again |
| element ref invalid | page re-rendered | re-run `snapshot -i` |
| `fill` has no effect | JS input listener | use `type` instead |
| HTTPS cert errors | self-signed / Burp CA | `ignoreHTTPSErrors: true` |
| page load timeout | heavy resources | longer timeout or `domcontentloaded` |
| UIA finds no controls | custom-drawn UI | switch to CUA mode |
| CUA clicks land off-target | DPI/resolution mismatch | screenshot first, verify coordinates |

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
