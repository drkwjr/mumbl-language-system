// Download the purchased LearnAkan bundle from Payhip, straight to the external drive.
// Payhip gates downloads behind JS (JWT + PDF stamping + credits), so drive the real page with a
// headless browser and let Payhip's own JS do the auth. Resume-safe: skips files already on disk
// WITHOUT clicking (credit-safe). PDFs -> OUT/, audio -> OUT/audio/.
//   NODE_PATH=$(npm root -g) node bank/ingest/download_learnakan.js [limit]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'https://payhip.com/d/l/bbe508aec53f79ace345e91f23d781c1c7a562f2';
const OUT = '/Volumes/DevVault/Projects/mumbl-language-system/bank/sources/learnakan';
const LIMIT = process.argv[2] ? parseInt(process.argv[2], 10) : Infinity;
const sanitize = s => s.replace(/\s+/g, ' ').trim();
// the 4 products in the bundle — audio Track names collide across guides, so route audio per product.
const PROD = { bg6xa: 'conversational', j8VJQ: 'vocabulary-companion', '4Oh7o': 'dictionary', F9BUA: 'idioms' };

(async () => {
  fs.mkdirSync(path.join(OUT, 'audio'), { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ acceptDownloads: true });
  const page = await ctx.newPage();
  console.log('loading download page...');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('a.download-btn', { timeout: 30000 });

  const rows = await page.$$('.file-row');
  console.log(`found ${rows.length} file rows (limit ${LIMIT})`);

  let ok = 0, skip = 0, fail = 0, n = 0;
  for (const row of rows) {
    if (n >= LIMIT) break;
    n++;
    const fnRaw = await row.$eval('.file-row-left p', el => el.textContent).catch(() => null);
    const btn = await row.$('a.download-btn');
    if (!fnRaw || !btn) { console.log(`  [${n}] no filename/button`); continue; }
    const fn = sanitize(fnRaw);
    const prodKey = await btn.getAttribute('data-prod-key');
    const sub = /\.mp3$/i.test(fn) ? path.join('audio', PROD[prodKey] || prodKey) : '';
    const dest = path.join(OUT, sub, fn);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (fs.existsSync(dest) && fs.statSync(dest).size > 1000) {
      skip++; console.log(`  [${n}/${rows.length}] skip  ${fn}`); continue;
    }
    const t0 = Date.now();
    try {
      const dlPromise = page.waitForEvent('download', { timeout: 240000 });
      await btn.click();
      const download = await dlPromise;
      await download.saveAs(dest);
      ok++;
      console.log(`  [${n}/${rows.length}] ok ${((Date.now() - t0) / 1000).toFixed(0)}s  ${fn}`);
    } catch (e) {
      fail++;
      console.log(`  [${n}/${rows.length}] FAIL  ${fn}: ${String(e).split('\n')[0].slice(0, 90)}`);
    }
  }
  console.log(`\ndone: ${ok} downloaded · ${skip} skipped · ${fail} failed -> ${OUT}`);
  await browser.close();
})();
