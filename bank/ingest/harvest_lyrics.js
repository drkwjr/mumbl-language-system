// Batched lyric harvest — crawl + render the whole 54-artist catalog in ONE warm browser.
// Fixes both throughput (no Chrome cold-start per URL) and resilience (short timeouts + skip on fail,
// so an artist not on AfrikaLyrics doesn't stall the run). Writes {artist,url,text} JSONL; the Twi
// capture + meaning/unknown partitioning happens in lyrics_catalog.py.
//   NODE_PATH=$(npm root -g) node bank/ingest/harvest_lyrics.js <artists.jsonl> <out.jsonl> [perArtist] [maxArtists]
const { chromium } = require('playwright');
const fs = require('fs');

const [ARTISTS, OUT] = [process.argv[2], process.argv[3]];
const PER = parseInt(process.argv[4] || '6', 10);
const MAX = parseInt(process.argv[5] || '54', 10);
const NAV = /sign up|top lyrics|submit|browse|countries|genres|albums|languages|forum|menu|cookie|subscribe|follow us|advertis|©|privacy|terms|all rights/i;

const slug = (n) => n.toLowerCase().replace(/'/g, '').replace(/\(asakaa\)/, '').trim().replace(/[^a-z0-9 ]/g, '').trim().replace(/ +/g, '-');

async function open(ctx, url, wait = 1500) {
  const p = await ctx.newPage();
  try {
    await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
    await p.waitForTimeout(wait);
    return p;
  } catch (e) {
    await p.close();
    return null;
  }
}

(async () => {
  const artists = fs.readFileSync(ARTISTS, 'utf8').trim().split('\n').map((l) => JSON.parse(l)).slice(0, MAX);
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext();
  const out = fs.createWriteStream(OUT);
  let songs = 0;

  for (const a of artists) {
    let urls = [];
    const ap = await open(ctx, `https://afrikalyrics.com/artist/${slug(a.name)}`, 2000);
    if (ap) {
      urls = await ap.$$eval('a[href*="-lyrics"]', (as) => as.map((x) => x.href)).catch(() => []);
      urls = [...new Set(urls.filter((h) => /-lyrics\/?$/.test(h) && !/\/(artist|genre|album|country|top-lyrics|category)/.test(h)))].slice(0, PER);
      await ap.close();
    }
    for (const u of urls) {
      const p = await open(ctx, u);
      if (!p) continue;
      const text = await p.evaluate((NAVsrc) => {
        const NAVre = new RegExp(NAVsrc, 'i');
        let best = '', bestScore = 0;
        for (const el of document.querySelectorAll('div,section,article,pre')) {
          const lines = (el.innerText || '').split('\n').map((s) => s.trim()).filter(Boolean);
          if (lines.length < 6) continue;
          if (lines.filter((l) => NAVre.test(l)).length > lines.length * 0.3) continue;
          const ly = lines.filter((l) => l.length >= 3 && l.length <= 90).length;
          if (ly > bestScore) { bestScore = ly; best = lines.join('\n'); }
        }
        return best;
      }, NAV.source).catch(() => '');
      await p.close();
      if (text) { out.write(JSON.stringify({ artist: a.name, url: u, text }) + '\n'); songs++; }
    }
    process.stderr.write(`  ${a.name}: ${urls.length} songs\n`);
  }
  out.end();
  await browser.close();
  process.stderr.write(`done: ${songs} songs -> ${OUT}\n`);
})();
