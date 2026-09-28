// Save the review screenshots to screenshots/.
//   node scripts/screenshots.js
// Starts its own static server on port 8793.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PORT = 8793;
const enc = encodeURIComponent;
const SHOTS = [
  ['01-john-1-1-parallel.png', '?view=table&b=John&c=1&v=John.1.1', false],
  ['02-psalm-23-across-columns.png', '?view=table&b=Ps&c=23', false],
  ['03-renderings-chesed.png', `?view=renderings&rc=he&rt=${enc('חסד')}&rm=contains`, true],
  ['04-sheol-saul-homograph.png', `?view=renderings&rc=he&rt=${enc('שאול')}&rm=contains`, true],
];

(async () => {
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '-d', path.join(ROOT, 'docs')], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1100 }, deviceScaleFactor: 1 });
    for (const [file, query, full] of SHOTS) {
      await page.goto(`http://localhost:${PORT}/${query}`);
      await page.waitForFunction(() => window.__polyglotReady === true);
      if (query.includes('renderings')) await page.waitForSelector('.rcard');
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(ROOT, 'screenshots', file), fullPage: full });
      console.log('saved', file);
    }
  } finally {
    await browser.close();
    server.kill();
  }
})();
