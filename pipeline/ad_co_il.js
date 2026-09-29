// ad.co.il scraper — SECOND SOURCE, no login and no bot protection.
// Run inside an ad.co.il tab via browser_console_evaluate.
//
// Why this site: every ad publishes schema.org Car JSON-LD (km, year, fuel, transmission)
// AND the page text carries TWO ownership fields Yad2 does not expose separately:
//   בעלות קודמת  = PREVIOUS ownership (ליסינג / חברה / פרטית / השכרה ...)
//   בעלות נוכחית = CURRENT  ownership
// So an ex-lease car now in private hands is detectable here — Yad2 gives only one field.
//
// Set window.__AD_CFG = { q: 'איוניק', label: 'Hyundai Ioniq (hybrid)', mustMatch: /היבריד/ }
// Result -> window.__AD_OUT
(async () => {
  const CFG = window.__AD_CFG || { q: 'קונה', label: 'Hyundai Kona' };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const pick = (s, re) => { const m = s.match(re); return m ? norm(m[1]) : null; };
  const numOf = s => { if (!s) return null; const d = String(s).replace(/[^\d]/g, ''); return d ? +d : null; };

  // ---- pass 1: collect ad ids for the query (all pages) ----
  const ids = new Set();
  let totalAds = null;
  for (let p = 1; p <= (CFG.maxPages || 15); p++) {
    const u = `https://www.ad.co.il/car?q=${encodeURIComponent(CFG.q)}` + (p > 1 ? `&page=${p}` : '');
    const r = await fetch(u, { credentials: 'include' });
    if (r.status !== 200) break;
    const t = await r.text();
    if (totalAds === null) totalAds = pick(t, /([\d,]+)\s*מודעות/);
    const found = [...new Set([...t.matchAll(/\/ad\/(\d+)/g)].map(m => m[1]))];
    const before = ids.size;
    found.forEach(i => ids.add(i));
    if (ids.size === before) break;                 // no new ads -> done
    await sleep(300);
  }

  // ---- pass 2: per-ad detail ----
  const cars = [];
  for (const id of ids) {
    try {
      const r = await fetch(`https://www.ad.co.il/ad/${id}`, { credentials: 'include' });
      if (r.status !== 200) { await sleep(250); continue; }
      const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
      const ld = [...doc.querySelectorAll('script[type="application/ld+json"]')]
        .map(s => { try { return JSON.parse(s.textContent); } catch (e) { return null; } }).filter(Boolean);
      const car = ld.find(x => String(x['@type'] || x.Type).includes('Car')) || {};
      const txt = norm(doc.body.innerText || doc.body.textContent);

      const name = car.name || pick(txt, /(יונדאי\s+\S+\s*\(\d{4}\))/);
      if (CFG.mustMatch && !CFG.mustMatch.test(txt)) { await sleep(220); continue; }

      cars.push({
        id, source: 'ad.co.il', url: `https://www.ad.co.il/ad/${id}`,
        name,
        year: car.VehicleModelDate?.[0] ?? numOf(pick(txt, /שנה\s*(\d{4})/)),
        km: car.MileageFromOdometer?.[0]?.Value?.[0] ?? numOf(pick(txt, /ק"מ\s*([\d,]+)/)),
        price: numOf(car.offers?.price) ?? numOf(pick(txt, /([\d,]{5,})\s*₪/)),
        hand: numOf(pick(txt, /יד\s*(\d+)/)),
        fuel: car.FuelType?.[0] ?? pick(txt, /סוג מנוע\s*(\S+)/),
        gear: car.VehicleTransmission?.[0] ?? pick(txt, /ת\. הילוכים\s*(\S+)/),
        engineVol: numOf(pick(txt, /נפח\s*([\d,]+)/)),
        color: pick(txt, /צבע\s*(\S+)/),
        ownerPrev: pick(txt, /בעלות קודמת\s*(\S+)/),      // ליסינג / חברה / פרטית ...
        ownerNow: pick(txt, /בעלות נוכחית\s*(\S+)/),
        region: pick(txt, /אזור\s*([^\d]+?)\s*עיר/),
        city: pick(txt, /עיר\s*(\S+)/),
        trim: pick(txt, /גרסה\s*([^\n]+?)(?=\s{2}|$)/),
      });
    } catch (e) { /* skip */ }
    await sleep(220);
  }

  // keep only cars whose CURRENT owner is private (matches the Yad2 private-seller framing)
  const priv = cars.filter(c => !c.ownerNow || /פרטית/.test(c.ownerNow));
  priv.sort((a, b) => (a.price ?? 9e9) - (b.price ?? 9e9));

  window.__AD_OUT = {
    label: CFG.label, source: 'ad.co.il', query: CFG.q,
    url: `https://www.ad.co.il/car?q=${encodeURIComponent(CFG.q)}`,
    scraped: new Date().toISOString().slice(0, 10),
    totalListings: numOf(totalAds), idsSeen: ids.size, scrapedCount: cars.length,
    privateCount: priv.length, cars: priv,
  };
  return JSON.stringify({
    label: CFG.label, totalAds, idsSeen: ids.size, detailed: cars.length, privateNow: priv.length,
    exLease: priv.filter(c => c.ownerPrev && !/פרטית/.test(c.ownerPrev)).length,
    withKm: priv.filter(c => c.km).length, withPrice: priv.filter(c => c.price).length,
  });
})()
