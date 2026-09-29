// Yad2 מחירון (official used-car price list) fetcher — v2 (2026-09-28). Run in a yad2.co.il tab.
//
// Endpoint: /price-list/feed?manufacturer=<id>&model=<id>
// __NEXT_DATA__.props.pageProps.models[] — one entry per (year, isNew). isNew:false = USED value.
// Each carries subModels[] {id, title, price, horsepower}.
//
// v1 keyed the list on "year|title" and joined listings by their title. Two real bugs:
//   1. Listing titles carry a generation suffix ("Supreme ... [2016-2019]") that price-list
//      titles lack -> exact match failed -> silently fell back to the year MEDIAN.
//   2. Yad2 lists TWO distinct sub-models under one title in the same year (two "Supreme FL",
//      ₪70,800 and ₪82,500). "byYearTrim[k] = price" kept whichever came last.
// v2 keys on subModels[].id — the same id space as a listing's subModel.id — and keeps the
// title map only as a fallback (suffix-stripped, and on collision it keeps the RANGE, not one value).
//
// Sets window.__PL = { byId:{subModelId:{price,year,title}}, byYearTrim:{"year|title":{min,max,n}}, byYear:{year:{min,max,med,n}} }
(async () => {
  const CFG = window.__YAD2_CFG || { manufacturer: 21, model: 10283 };
  const norm = s => (s || '').replace(/\s*\[\d{4}-\d{4}\]\s*$/, '').replace(/\s+/g, ' ').trim();
  const r = await fetch(`https://www.yad2.co.il/price-list/feed?manufacturer=${CFG.manufacturer}&model=${CFG.model}`,
                        { credentials: 'include' });
  const el = (new DOMParser().parseFromString(await r.text(), 'text/html')).getElementById('__NEXT_DATA__');
  if (!el) return JSON.stringify({ error: 'no __NEXT_DATA__' });
  const models = JSON.parse(el.textContent).props?.pageProps?.models || [];

  const byId = {}, byYearTrim = {}, byYear = {};
  for (const m of models) {
    if (m.isNew) continue;
    const ps = [];
    for (const s of (m.subModels || [])) {
      if (!s.price) continue;
      // key on year|id: the SAME sub-model id recurs across years with a different used
      // price each year, so keying on id alone silently keeps only the last year seen.
      if (s.id) byId[`${m.year}|${s.id}`] = { price: s.price, year: m.year, title: norm(s.title) };
      const k = `${m.year}|${norm(s.title)}`;
      const e = byYearTrim[k] || (byYearTrim[k] = { min: s.price, max: s.price, n: 0 });
      e.min = Math.min(e.min, s.price); e.max = Math.max(e.max, s.price); e.n++;
      ps.push(s.price);
    }
    if (ps.length) { ps.sort((a, b) => a - b); byYear[m.year] = { min: ps[0], max: ps[ps.length - 1], med: ps[ps.length >> 1], n: ps.length }; }
  }
  window.__PL = { byId, byYearTrim, byYear, source: 'yad2 price-list (מחירון)', fetched: new Date().toISOString().slice(0, 10) };
  const coll = Object.values(byYearTrim).filter(e => e.n > 1 && e.max !== e.min).length;
  return JSON.stringify({ ids: Object.keys(byId).length, titleKeys: Object.keys(byYearTrim).length, titleCollisions: coll, years: Object.keys(byYear) });
})()
