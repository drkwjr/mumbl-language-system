// Crawl an AfrikaLyrics artist page for that artist's song-lyric URLs (Playwright — the page is JS).
// Used by lyrics_catalog.py to turn the 54-artist seed into per-song URLs for the lyric ingestion.
//   NODE_PATH=$(npm root -g) node bank/ingest/crawl_artist.js <artist-page-url> [cap]
const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2];
  const cap = parseInt(process.argv[3] || '8', 10);
  if (!url) { process.stderr.write('no url'); process.exit(1); }
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    const links = await page.$$eval('a[href*="-lyrics"]', (as) => as.map((a) => a.href));
    const uniq = [...new Set(links.filter((h) => /-lyrics\/?$/.test(h)
      && !/\/(artist|genre|album|country|top-lyrics|category)/.test(h)))].slice(0, cap);
    process.stdout.write(uniq.join('\n'));
  } catch (e) {
    process.stderr.write(String(e).slice(0, 120));
  }
  await browser.close();
})();
