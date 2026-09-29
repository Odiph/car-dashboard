// Yad2 private-seller scraper — v2 (2026-09-25).
// Reads Yad2's OWN embedded JSON (__NEXT_DATA__), not the DOM/CSS classes.
//
// WHY v2: v1 classified sellers by CSS class (private-item-module / agency-item-module).
// Those classes describe CARD LAYOUT and only exist for the ~17 server-rendered rows per page;
// the other ~23 rows hydrate client-side. v1 therefore saw 22 of 131 private Konas and
// reported private sellers as 7% of the market when the true figure is 42%.
// adType in the feed JSON is Yad2's OWN label. Never infer seller type any other way.
//
// Run inside a yad2.co.il tab via browser_console_evaluate (the page carries the session;
// plain Python/Node is blocked by Radware). Returns a compact summary; full rows go to window.__OUT.
(async () => {
  const CFG = window.__YAD2_CFG || { manufacturer: 21, model: 10283, label: 'Hyundai Kona' };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const base = `https://www.yad2.co.il/vehicles/cars?manufacturer=${CFG.manufacturer}&model=${CFG.model}`;

  const nd = async url => {
    const r = await fetch(url, { credentials: 'include' });
    if (r.status !== 200) return { status: r.status };
    const el = (new DOMParser().parseFromString(await r.text(), 'text/html')).getElementById('__NEXT_DATA__');
    return el ? { status: 200, json: JSON.parse(el.textContent) } : { status: 200 };
  };

  // ---------- pass 1: every ad from the feed JSON, classified by adType ----------
  const feed = new Map();
  let total = null, pages = null, counts = {};
  for (let p = 1; p <= (CFG.maxPages || 40); p++) {
    const { json } = await nd(`${base}&page=${p}`);
    if (!json) break;
    const q = (json.props?.pageProps?.dehydratedState?.queries || []).find(x => x.state?.data?.ads);
    if (!q) break;
    const pg = q.state.data.pagination || {};
    total = pg.total ?? total; pages = pg.pages ?? pages;
    for (const a of q.state.data.ads) {
      counts[a.adType] = (counts[a.adType] || 0) + 1;
      if (feed.has(a.token)) continue;
      feed.set(a.token, {
        id: a.token, adType: a.adType, price: a.price ?? null,
        year: a.vehicleDates?.yearOfProduction ?? null,
        trim: a.subModel?.text ?? null, hand: a.hand?.id ?? null,
        // subModel.id is the SAME id space as the מחירון price-list subModels[].id.
        // Join the price list on THIS, never on the title: titles carry generation
        // suffixes ("[2016-2019]") the price list lacks, and Yad2 lists two distinct
        // sub-models under one title (two "Supreme FL" per year, different prices).
        subModelId: a.subModel?.id ?? null,
        area: a.address?.area?.text ?? null, images: a.metaData?.images?.length || 0,
        created: (a.createdAt || '').slice(0, 10),
      });
    }
    if (pages && p >= pages) break;
    await sleep(140);
  }

  const wanted = CFG.adType === 'all' ? [...feed.values()]
               : [...feed.values()].filter(a => a.adType === (CFG.adType || 'private'));

  // ---------- pass 2: per-ad detail, also from JSON ----------
  const cars = [];
  for (const row of wanted) {
    const { status, json } = await nd(`https://www.yad2.co.il/vehicles/item/${row.id}`);
    if (status !== 200 || !json) { cars.push({ ...row, gone: 1 }); await sleep(90); continue; }
    const d = json.props?.pageProps?.dehydratedState?.queries?.[0]?.state?.data;
    if (!d) { cars.push({ ...row, gone: 1 }); await sleep(90); continue; }

    const km = d.km ?? null;
    const yr = d.vehicleDates?.yearOfProduction, mo = d.vehicleDates?.monthOfProduction?.id || 6;
    let kmyr = null;
    if (km && yr) {
      const age = (Date.now() - new Date(yr, mo - 1, 1).getTime()) / 3.15576e10;
      if (age > 0.15) kmyr = Math.round(km / age);
    }
    cars.push({
      ...row, km, kmyr,
      price: d.price ?? row.price,
      // NOTE: d.abovePrice is a coarse search bucket, NOT a valuation. Deliberately not captured.
      // Price comparison is done downstream against peer medians per model-year.
      color: d.color?.textEng || d.color?.text || null,
      owner: d.owner?.text || null,                       // פרטית = private since new
      gear: d.gearBox?.textEng || d.gearBox?.text || null,
      fuel: d.engineType?.textEng || d.engineType?.text || null,
      body: d.bodyType?.text || null,
      hp: d.horsePower ?? null, engineVol: d.engineVolume ?? null,
      seats: d.seats ?? null, doors: d.numberOfDoors ?? null,
      drive: d.specification?.ignition?.text || null,
      turbo: d.specification?.isTurbo ?? null,
      safety: d.specification?.safetyPoints ?? null,
      pollution: d.specification?.pollutionLevel ?? null,
      test: (d.vehicleDates?.testDate || '').slice(0, 10) || null,
      city: d.address?.city?.textEng || d.address?.city?.text || null,
      region: d.address?.topArea?.text || null,
      posted: (d.dates?.createdAt || '').slice(0, 10) || null,
      updated: (d.dates?.updatedAt || '').slice(0, 10) || null,
    });
    await sleep(90);
  }

  cars.sort((a, b) => (a.price ?? 9e9) - (b.price ?? 9e9));
  window.__OUT = {
    label: CFG.label, url: base, scraped: new Date().toISOString().slice(0, 10),
    totalListings: total, pages, feedCounts: counts, uniqueAds: feed.size,
    adTypeFilter: CFG.adType || 'private', privateCount: cars.filter(c => !c.gone).length,
    commercialCount: [...feed.values()].filter(a => a.adType === 'commercial').length, cars,
  };
  return JSON.stringify({
    label: CFG.label, totalListings: total, pages, uniqueAds: feed.size, byType: counts,
    scraped: cars.length, withKm: cars.filter(c => c.km).length, gone: cars.filter(c => c.gone).length,
  });
})()
