// konesy2.co.il repossession/receiver auction scraper — v1 (2026-09-29).
// Run inside a konesy2.co.il tab via browser_console_evaluate. No login needed: plain fetch
// returns every field including prices (verified). No API — server-rendered HTML, labelled text.
//
// SHAPE: auctions are NOT listings. There is no asking price. A lot carries either
//   "מחיר התחלתי: N"        = opening bid (no bids yet), or
//   "ההצעה המובילה היא: N"  = current top bid (bidding under way)
// plus an auction date/countdown and a status. Never mix these into the Yad2 price column —
// an opening bid next to an asking price reads as a fake 40% discount.
//
// TRAP (2026-09-29): a lot's DETAIL page does not show its own price; the only prices on it are
// in the "next auctions" sidebar (other cars). Take price + status from the CATALOGUE card, and
// car facts (km, trim, year, hand, ownership, license) from the detail page.
//
// CFG: window.__KONESY_CFG = { makeId: 218 /* יונדאי */, models: [ {label:'Hyundai Kona', re:/קונה|KONA/i, exclude:/ELECTRIC|EV/i},
//                                                            {label:'Hyundai Ioniq (hybrid)', re:/איוניק|IONIQ/i, exclude:/IONIQ ?[56]/i} ] }
// Result -> window.__KONESY_OUT = { fetched, lots:[...] }; returns a compact summary.
(async () => {
  const CFG = window.__KONESY_CFG || { makeId: 218, models: [] };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const num = s => { const d = String(s || '').replace(/[^\d]/g, ''); return d ? +d : null; };
  const pick = (t, re) => { const m = t.match(re); return m ? norm(m[1]) : null; };
  const html = async u => { const r = await fetch(u, { credentials: 'include' }); return r.status === 200 ? await r.text() : null; };
  const doc = h => new DOMParser().parseFromString(h, 'text/html');
  const text = d => norm(d.body.innerText || d.body.textContent);

  // ---- pass 1: catalogue cards (price + status live here) ----
  const cards = new Map();
  for (let p = 1; p <= (CFG.maxPages || 30); p++) {
    const h = await html(`https://konesy2.co.il/Cars?CategoryId=1&CarType=1&CarMakeIds=${CFG.makeId}${p > 1 ? '&page=' + p : ''}`);
    if (!h) break;
    const d = doc(h); const before = cards.size;
    for (const a of d.querySelectorAll('a[href*="/live/"]')) {
      const id = (a.getAttribute('href').match(/\/live\/(\d+)/) || [])[1]; if (!id) continue;
      let card = a; for (let i = 0; i < 6 && card.parentElement; i++) { card = card.parentElement; if (/מחיר התחלתי|ההצעה המובילה/.test(card.textContent)) break; }
      const t = norm(card.innerText || card.textContent);
      if (!/מחיר התחלתי|ההצעה המובילה/.test(t)) continue;          // not a lot card
      if (cards.has(id)) continue;
      cards.set(id, {
        id, url: `https://konesy2.co.il/live/${id}`,
        title: pick(t, /(?:בהסכמתו|בזמן הקרוב|בשעה \d{1,2}:\d{2}|בעוד[^א-ת]*)\s+((?:יונדאי|[A-Za-z֐-׿]+)\s+[^:]+?)\s+(?:מחיר התחלתי|ההצעה המובילה)/) || t.slice(0, 60),
        openingBid: num(pick(t, /מחיר התחלתי[:\s]*([\d,]+)/)),
        topBid: num(pick(t, /ההצעה המובילה היא[:\s]*([\d,]+)/)),
        sellerType: pick(t, /^(בא כוח|כונס נכסים|רשות המיסים|נאמן|מנהל מיוחד)/) || pick(t, /(בא כוח|כונס נכסים|רשות המיסים|נאמן)/),
        statusText: pick(t, /(מתחילים בעוד[^י]*|מתחילים בזמן הקרוב|מתחילים מחר בשעה \d{1,2}:\d{2}|מתחילים היום[^י]*|LIVE|נמכר|הסתיים)/),
      });
    }
    if (cards.size === before) break;
    await sleep(350);
  }

  // ---- pass 2: keep only the models we track ----
  const match = c => CFG.models.find(m => m.re.test(c.title) && !(m.exclude && m.exclude.test(c.title)));
  const wanted = [...cards.values()].filter(c => match(c));

  // ---- pass 3: detail page per lot (facts only — NOT price) ----
  const lots = [];
  for (const c of wanted) {
    const h = await html(c.url); if (!h) { lots.push({ ...c, gone: 1 }); await sleep(300); continue; }
    const t = text(doc(h));
    const blk = t.slice(Math.max(0, t.indexOf('פרטי המכרז')), t.indexOf('מגוון רכבים בעד') > 0 ? t.indexOf('מגוון רכבים בעד') : undefined);
    const auctionAt = pick(t, /מועד המכרז (\d{2}\/\d{2}\/\d{4} \d{2}:\d{2})/);
    let auctionIso = null;
    if (auctionAt) { const [dd, mm, yy, hh, mi] = auctionAt.match(/\d+/g).map(Number); auctionIso = new Date(yy, mm - 1, dd, hh, mi).toISOString(); }
    // STATUS: never grep the page text for "נמכר" — it appears in the site's own boilerplate
    // ("רכב זה נמכר מטעם ובשם בעליו") on EVERY lot, which marked all 11 tracked lots "closed".
    // Derive it from the auction date instead; "live" only when the date has passed within the
    // last day and the page still shows a LIVE marker near the top.
    const head = t.slice(0, 1500);
    let status = 'upcoming';
    if (auctionIso) {
      const ms = new Date(auctionIso) - Date.now();
      if (ms < -864e5) status = 'closed';
      else if (ms <= 0) status = /LIVE/.test(head) ? 'live' : 'closed';
    }
    lots.push({
      ...c, model: match(c).label, source: 'konesy2',
      year: num(pick(blk, /שנה (\d{4})/)), km: num(pick(blk, /קילומטראז' (\d+)/)),
      trim: pick(blk, /רמת גימור (.+?) סוג מנוע/), fuel: pick(blk, /סוג מנוע (\S+)/), gear: pick(blk, /סוג גיר (\S+)/),
      engineVol: num(pick(blk, /נפח מנוע (\d+)/)), condition: pick(blk, /מצב המוצר (\S+)/),
      // colour: stop at the next field label. "סוג" alone (not just "סוג פרטי") — some lots say "סוג כללי ב"כ הבעלים…"
      // and the old lookahead let the colour swallow half a sentence ("שנהב לבן סוג כללי ב"כ הבעלים. רכב מניע…").
      color: pick(blk, /צבע (.+?) (?:סוג |יד \d|גלגלי|בקרת|קבוצת|תוקף)/), hand: num(pick(blk, /יד (\d+)/)),
      // sealed-bid lots put the trim (e.g. "היבריד FL") in the TITLE, not in the details block
      trimFromTitle: (c.title.match(/\b(PREMIUM|SUPREME|PRIME ?PLUS|PRIME|INSPIRE|INTENSE|CLASSIC|PRESTIGE|LUXURY)\b(?:\s+FL)?/i) || [])[0]
                   || (/היבריד FL|FL/.test(c.title) ? 'PREMIUM FL' : null),
      // ownership: only accept an ownership WORD after "יד N" — on some lots the next token is a
      // different field label ("קילומטראז'"), which a bare \S+ swallowed.
      ownership: (blk.match(/יד \d+ (ליסינג|פרטית|פרטי|חברה|השכרה|מונית|לימוד)/) || [])[1] || (blk.match(/\b(ליסינג|השכרה|חברה)\b/) || [])[1] || null,
      licenseValid: pick(blk, /תוקף רישיון: ([\d.]+)/), pollution: num(pick(blk, /קבוצת זיהום: (\d+)/)),
      published: pick(blk, /תאריך פרסום (\d{2}\/\d{2}\/\d{2})/), submitBy: pick(blk, /מועד הגשה (\d{2}\/\d{2}\/\d{2})/),
      auctionAt, auctionIso, status,
      priceKind: c.topBid ? 'top' : (c.openingBid ? 'opening' : 'sealed'),   // כונס נכסים lots publish no price
    });
    if (!lots[lots.length - 1].trim && lots[lots.length - 1].trimFromTitle) lots[lots.length - 1].trim = lots[lots.length - 1].trimFromTitle;
    await sleep(300);
  }

  // ---- pass 4: closed / gone lots we tracked before, so sold prices survive as calibration ----
  window.__KONESY_OUT = { fetched: new Date().toISOString(), makeId: CFG.makeId, catalogueLots: cards.size, lots };
  return JSON.stringify({
    catalogueLots: cards.size, tracked: lots.length,
    byModel: Object.fromEntries(CFG.models.map(m => [m.label, lots.filter(l => l.model === m.label).length])),
    byStatus: lots.reduce((a, l) => (a[l.status] = (a[l.status] || 0) + 1, a), {}),
    sample: lots.slice(0, 2),
  });
})()
