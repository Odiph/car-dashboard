# Daily refresh — what the 03:00 task must do

The scrape CANNOT run headless: Yad2 sits behind Radware bot protection, so every fetch has to
happen inside a real logged-in browser tab (`browser_console_evaluate` against a `yad2.co.il` tab).
That is why this is a Scotty Scheduled Task and not a plain cron job.

## Models tracked

| Label | manufacturer | model | filter |
|---|---|---|---|
| Hyundai Kona | 21 | 10283 | private sellers |
| Hyundai Ioniq (hybrid) | 21 | 10279 | private sellers, hybrid only |

## Sequence

1. Open/reuse a background tab on `https://www.yad2.co.il/vehicles/cars`.
2. For each model, run `scrape.js` (feed pass, then detail pass) with `window.__YAD2_CFG` set.
   Pace it: **~350 ms between requests, batches of ~8**. Faster than that tripped the bot wall at
   roughly 430 consecutive fetches and wiped a full run.
   Progress is checkpointed to `localStorage` after every car, so a block loses nothing.
3. Run `pricelist.js` per model to refresh the מחירון, then `merge_pricelist.py` to join it.
4. Rebuild: `yad2_xlsx.py` per model, then `make_dashboard.py` for the combined dashboard.
5. Write outputs to `~/Downloads` AND `~/Desktop`.
6. **Publish.** Live site: https://odiph.github.io/car-dashboard/ (GitHub Pages, repo `Odiph/car-dashboard`,
   branch `main`, root). Local clone at `C:\Users\Paneth LEVTOV\car-dashboard` with git identity already set.
   `cp car-dashboard.html index.html && git add index.html && git commit -m "Daily refresh <date>" && git push origin main`.
   On rejection: `git pull --rebase origin main` then push again.

## מחירון join rule (2026-09-28) — do not regress this

Join the price list on **year + `subModel.id`** (`scrape.js` captures `subModelId`; `pricelist.js`
keys `byId` on `year|id`). Title-based joining produced wrong values two ways:
- listing titles carry a generation suffix (`Supreme … [2016-2019]`) that price-list titles lack →
  no match → silently fell to the year median (a 2018 Ioniq Supreme showed ₪55,900 instead of ₪64,300);
- Yad2 lists two different sub-models under one title in the same year (two `Supreme FL`, ₪70,800 and
  ₪82,500) → the last one seen won.
And never key on `id` alone: the same sub-model id recurs across years with a different price each
year (41 Kona / 15 Ioniq ids span years). Fallback order is id → suffix-stripped title (range if
ambiguous, shown with `~`) → year median (shown with `*`).

## Getting data out of the browser (2026-09-28) — downloads are NOT reliable

The blob-`<a download>` trick works for the FIRST automatic download on a page and is then
silently blocked (Chrome's automatic-downloads permission). Two runs lost their price list this
way and one of them **pushed a stale build live under a "fix" commit**. Rules:
- Never let a rebuild proceed on a missing input: gate every step (`[ -s file ] || exit 1`,
  `python step || exit 1`) and spot-check known rows BEFORE `git push`.
- Prefer returning compact JSON from `browser.console.evaluate` and writing it to disk yourself;
  keep each return under ~10 KB or it is offloaded and cannot be recovered to disk. Split by model
  and by map (`byId`+`byYear` in one call, `byYearTrim` as `[key,min,max,n]` rows in another).
- If you must download, navigate the tab to a fresh page first — the block is per-document.

## Caching gotcha (2026-09-28)

The page carries `Cache-Control: no-cache` meta tags because a browser tab served from the local
`python -m http.server` showed a 2-day-old copy and fired the "refresh may have stopped" warning
while the file on disk was fresh. If the live page ever looks stale, hard-reload first
(Ctrl+F5) before assuming the task failed; then check the task's run history.

## Auctions mode — konesy2.co.il (2026-09-29)

Repossession / receiver auctions for the same two models, shown as a **separate mode** (Show: Private
listings | Auctions). They are never merged into `cars` — there is no asking price, so an opening bid
next to a Yad2 asking price would read as a fake discount.

- Scrape with `konesy2.js` in a konesy2.co.il tab (no login needed; plain fetch returns prices).
  Catalogue: page 1 is HTML at `/Cars?CategoryId=1&CarType=1&CarMakeIds=218`, pages 2+ are
  `POST /Cars/GetLotsPartial` (`CarTypeId=&page=N&CarMakeIds[]=218`, JSON `{view}`), 20 lots/page.
  Hyundai make id = 218. Exclude `IONIQ ?[56]` (EVs) and Kona `ELECTRIC`.
- **Price comes from the catalogue card, facts from the detail page.** A lot's detail page shows
  OTHER lots' prices in its "next auctions" sidebar — grabbing the first price there attributes a
  Suzuki's ₪59,900 to an Ioniq. Card price forms: `מחיר התחלתי: N` (opening) or `ההצעה המובילה היא: N`
  (current top bid). `כונס נכסים` lots publish **no price at all** (sealed bids) → `priceKind: sealed`.
- **Status is derived from the auction date, never from the word "נמכר"** — that word is in the site's
  boilerplate on every lot and marked all 11 tracked lots "closed" on the first run.
- Then `python merge_auctions.py konesy2.json pl_v2.json yad2_kona_v2.json yad2_ioniq.json`: adds מחירון
  (auction trims are terse uppercase, e.g. `PREMIUM FL` — matched as a prefix of same-year list titles),
  `headroomVsList` (ceiling, not discount), `estAllIn` (**assumed** fee — konesy2 publishes none; only a
  5% subscription-cancellation clause exists), `daysToAuction`, and appends a per-lot `auctionHistory`
  snapshot so clearing prices accumulate — the site has no sold archive.
- Refresh daily with the rest: countdowns that are days stale are worse than none.
- **Auction trim → מחירון join** (`merge_auctions.match_list`): konesy2 trims are terse and messy —
  glued (`PRIMEPLUS FL`), sometimes Hebrew (`פרימיום`), and carry `FL` even where the list has no FL
  variant for that trim. Normalise (split glued words, transliterate, try with and without FL), match as a
  prefix of same-year list titles while rejecting `PLUS`/`FL` continuations (`PRIME` must not hit
  `Prime Plus`), and on several hits keep the shortest trim-word span. A remaining range is REAL: Yad2
  lists two sub-models under one title (2023 Kona "Prime אוט׳ 1.6" at ₪93,700 and ₪135,400) — show
  the midpoint with `~`, never pick one. Gate: every lot that has a trim must join at `trim` or
  `trim-range`; only trimless (sealed כונס) lots may use `year-median`. Sealed lots have no bid, so no
  headroom / all-in — leave them blank, not zero.

## Files

- `scrape.js` — listings (adType-classified; never infer seller type from CSS)
- `pricelist.js` — official used-car מחירון per year+trim
- `merge_pricelist.py` — joins מחירון onto a scrape JSON
- `yad2_xlsx.py` — Excel workbook
- `make_dashboard.py` — combined single-file dashboard (stamps its own build time)
- `ad_co_il.js` — optional second source, not currently wired into the dashboard

## Known gaps

- The Ioniq dataset is missing `images` and `turbo` (a hand-written loop during a rate-limit
  incident omitted them). The next full re-scrape via `scrape.js` restores both.
- Service history and accident history are never published by Yad2 — they need a בדיקת רכב.
- gov.il ownership/lien lookups need the plate number, which ads do not show.
