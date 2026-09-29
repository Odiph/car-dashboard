# -*- coding: utf-8 -*-
"""Attach konesy2 auction lots to the dashboard data, as a SEPARATE mode.  v1 (2026-09-29)

    python merge_auctions.py konesy2.json yad2_pricelist.json yad2_kona_v2.json yad2_ioniq.json

Auctions are not listings — no asking price, a deadline, and an as-is sale. They are stored under
each model's `auctions` key (never mixed into `cars`) so the dashboard can show/hide them as a mode
and never puts an opening bid next to an asking price in the same column.

Per lot we add:
  listPrice / listPriceBasis  - Yad2 מחירון for year+trim (title match; auction trims are uppercase)
  bidRef                      - the number to reason from: topBid if bidding started, else openingBid
  headroomVsList              - listPrice / bidRef - 1  (how far the bid COULD rise before reaching book)
  estAllIn                    - bidRef * (1 + FEE_PCT) — buyer fee is NOT published by the site; this is an
                                explicit assumption (default 8%) and is labelled as such in the UI
  daysToAuction               - from auctionIso vs the scrape time (negative = past)
Also keeps a rolling `auctionHistory` per lot id (bid snapshots by date) so sold prices accumulate
as calibration — the site has no sold archive, so this is the only way to learn what lots clear at.
"""
import json, sys, re, datetime as dt

FEE_PCT = 0.08   # assumption, not a published figure — surfaced as such in the dashboard

def norm(s):
    s = re.sub(r"\s*\[\d{4}-\d{4}\]\s*$", "", s or "")
    return re.sub(r"\s+", " ", s).strip()

def match_list(lot, by_trim, by_year):
    """Auction trims are terse and uppercase ('PREMIUM FL'); price-list titles are long.
    Match on year + the trim words appearing (in order) at the start of a same-year title."""
    y = lot.get("year")
    if not y: return None, None
    # konesy2 trims are terse, uppercase and sometimes glued: "PRIMEPLUS FL", "PRIME FL".
    # Normalise to compare against the list: split glued words, and treat "FL" as optional —
    # the price list only carries an FL variant for some trims (Prestige FL yes, Prime FL no),
    # so a "PRIME FL" auction lot should still match the "Prime" list title, not fall to the year median.
    raw = (lot.get("trim") or "").upper().replace("PRIMEPLUS", "PRIME PLUS").replace("PREMIUMPLUS", "PREMIUM PLUS")
    # some lots write the trim in Hebrew ("פרימיום") — map to the Latin names the price list uses
    HE = {"פרימיום": "PREMIUM", "סופרים": "SUPREME", "פרסטיג'": "PRESTIGE", "פרסטיז'": "PRESTIGE", "פריים": "PRIME", "קלאסיק": "CLASSIC", "אינספייר": "INSPIRE"}
    raw = " ".join(HE.get(w, w) for w in raw.split())
    t = raw.split()
    cands = [(k, v) for k, v in by_trim.items() if k.startswith(f"{y}|")]
    if t:
        def words_of(k): return norm(k.split("|", 1)[1]).upper().split()
        attempts = [t]
        if "FL" in t: attempts.append([w for w in t if w != "FL"])           # drop FL
        hits = []
        for tt in attempts:
            # exact-prefix match first ("PRIME PLUS" must not match "Prime"), so require the list title's
            # own trim words to end where ours do: next word must not be PLUS/FL
            for k, v in cands:
                w = words_of(k)
                if w[:len(tt)] == tt and (len(w) == len(tt) or w[len(tt)] not in ("PLUS", "FL")):
                    hits.append(v)
            if hits: break
        # the same trim name can appear more than once in a year (two "Prime" titles with different
        # engines/prices). When the lot has an engine size, prefer the title whose cc matches; otherwise
        # keep the range — the ~ marker tells the user it is a spread, not a point value.
        # "PRIME FL" must not resolve to a range spanning both "Prime" and "Prime Plus". The prefix
        # rule already rejects PLUS/FL continuations, but two distinct list titles can still share
        # the trim words (different engine / generation). Prefer the title whose trim-word span is
        # SHORTEST — the closest to the auction's terse name — and only keep a range on a true tie.
        # FUEL first: the same trim exists as hybrid AND electric in one year ("Premium היברידי"
        # ₪63,100 vs "Premium חשמלי" ₪58,500 for 2019 Ioniq). Averaging them is wrong. The Ioniq
        # set is hybrid-only by construction, and konesy2 gives fuel for most lots — drop
        # electric titles unless the lot itself is electric.
        if len(hits) > 1:
            fuel = (lot.get("fuel") or "").strip()
            lot_is_ev = fuel in ("חשמלי", "חשמל", "חשמלית")
            model_hybrid_only = "hybrid" in (lot.get("model") or "").lower()
            if not lot_is_ev and (model_hybrid_only or fuel):
                non_ev = [v for k, v in cands if v in hits and "חשמלי" not in k.split("|", 1)[1]]
                if non_ev: hits = non_ev
        if len(hits) > 1:
            def trim_words(k):
                w = words_of(k); n = 0
                for x in w:
                    if x in ("PRIME","PLUS","FL","PREMIUM","SUPREME","PRESTIGE","CLASSIC","INSPIRE","INTENSE","LUXURY","N","LINE","OPEN","SKY","4X2","4X4"): n += 1
                    else: break
                return n
            scored = sorted(((trim_words(k), v) for k, v in cands if v in hits), key=lambda x: x[0])
            best = scored[0][0]
            hits = [v for n, v in scored if n == best]
        if hits:
            prices = [h["min"] for h in hits] + [h["max"] for h in hits]
            lo, hi = min(prices), max(prices)
            return (round((lo + hi) / 2), "trim") if lo == hi else (round((lo + hi) / 2), "trim-range")
    ym = by_year.get(str(y)) or by_year.get(y)
    return (ym["med"], "year-median") if ym else (None, None)

def main(auc_path, pl_path, *data_paths):
    auc = json.load(open(auc_path, encoding="utf-8"))
    pl = json.load(open(pl_path, encoding="utf-8"))
    fetched = auc.get("fetched") or dt.datetime.now().isoformat()
    now = dt.datetime.fromisoformat(fetched.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    today = now.date().isoformat()

    for p in data_paths:
        d = json.load(open(p, encoding="utf-8"))
        key = "kona" if "Kona" in d["label"] else "ioniq"
        by_trim, by_year = pl[key]["byYearTrim"], pl[key]["byYear"]
        hist = d.get("auctionHistory", {})
        lots = []
        for lot in auc["lots"]:
            if lot.get("model") != d["label"]: continue
            lp, basis = match_list(lot, by_trim, by_year)
            ref = lot.get("topBid") or lot.get("openingBid")
            days = None
            if lot.get("auctionIso"):
                a = dt.datetime.fromisoformat(lot["auctionIso"].replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
                days = round((a - now).total_seconds() / 86400, 1)
            lots.append({**lot, "listPrice": lp, "listPriceBasis": basis, "bidRef": ref,
                         "bidKind": "top" if lot.get("topBid") else ("opening" if lot.get("openingBid") else None),
                         "headroomVsList": (round(lp / ref - 1, 4) if (lp and ref) else None),
                         "estAllIn": (round(ref * (1 + FEE_PCT)) if ref else None), "feePctAssumed": FEE_PCT,
                         "daysToAuction": days})
            h = hist.setdefault(lot["id"], [])
            snap = {"date": today, "opening": lot.get("openingBid"), "top": lot.get("topBid"), "status": lot.get("status")}
            if not h or h[-1] != {**h[-1], **snap} or h[-1].get("date") != today:
                if not h or h[-1].get("date") != today: h.append(snap)
                else: h[-1] = snap
        d["auctions"] = lots
        d["auctionHistory"] = hist
        d["auctionsMeta"] = {"source": "konesy2.co.il", "fetched": fetched, "feePctAssumed": FEE_PCT,
                             "note": "Buyer fee is not published by konesy2; estAllIn uses an assumed %."}
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"{d['label']}: {len(lots)} auction lots | " +
              ", ".join(f"{l['id']} {l.get('year')} {l.get('trim')} bid {l['bidRef']} list {l['listPrice']}({l['listPriceBasis']}) in {l['daysToAuction']}d" for l in lots))

if __name__ == "__main__":
    main(*sys.argv[1:])
