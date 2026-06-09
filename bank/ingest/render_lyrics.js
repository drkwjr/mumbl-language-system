// Render a lyric page and return the lyric block as CLEAN text — the robust fetcher for the lyric
// ingestion. Playwright renders the JS (beats AfrikaLyrics/Genius) AND innerText preserves real line
// breaks (beats the raw-HTML parse that glued words across lines, e.g. "problemyɛɛ"). Source-agnostic:
// finds the densest non-nav multi-line text block on the page. Prints the lyric text to stdout.
//   NODE_PATH=$(npm root -g) node bank/ingest/render_lyrics.js <url>
const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2];
  if (!url) { process.stderr.write('no url'); process.exit(1); }
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(1500);
    const text = await page.evaluate(() => {
      const NAV = /sign up|top lyrics|submit|browse|countries|genres|albums|languages|forum|menu|cookie|subscribe|follow us|advertis|©|privacy|terms|all rights/i;
      let best = '', bestScore = 0;
      for (const el of document.querySelectorAll('div,section,article,pre')) {
        const lines = (el.innerText || '').split('\n').map((s) => s.trim()).filter(Boolean);
        if (lines.length < 6) continue;
        const navLines = lines.filter((l) => NAV.test(l)).length;
        if (navLines > lines.length * 0.3) continue; // mostly chrome
        const lyricLines = lines.filter((l) => l.length >= 3 && l.length <= 90).length;
        if (lyricLines > bestScore) { bestScore = lyricLines; best = lines.join('\n'); }
      }
      return best;
    });
    process.stdout.write(text || '');
  } catch (e) {
    process.stderr.write(String(e).slice(0, 120));
  }
  await browser.close();
})();
