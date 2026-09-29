# -*- coding: utf-8 -*-
"""Join Yad2's official מחירון (used-car price list) onto a scrape JSON, in place.  v2 (2026-09-28)

    python merge_pricelist.py yad2_pricelist.json kona yad2_kona_v2.json

Join order, per listing:
  1. subModelId  -> exact price for THIS sub-model   (basis 'id')        <- the correct join
  2. year|title  -> title match, suffix-stripped      (basis 'trim' if unambiguous,
                                                       'trim-range' if Yad2 lists 2+ prices under it)
  3. year median                                       (basis 'year-median', shown with *)

Adds per listing: listPrice, listPriceBasis, listPriceMin/Max (range basis only), vsList.

v1 joined on title only and had two real bugs: generation suffixes ("[2016-2019]") broke the match
and dropped rows to the year median; and duplicate titles (two "Supreme FL" per year) silently kept
the last price seen. Both produced מחירון values that were wrong for the car shown.
"""
import json, sys, re, statistics as st

def norm(s):
    s = re.sub(r"\s*\[\d{4}-\d{4}\]\s*$", "", s or "")
    return re.sub(r"\s+", " ", s).strip()

def main(pl_path, key, data_path):
    plfile = json.load(open(pl_path, encoding="utf-8"))
    pl = plfile[key]
    by_id, by_trim, by_year = pl.get("byId", {}), pl.get("byYearTrim", {}), pl.get("byYear", {})
    d = json.load(open(data_path, encoding="utf-8"))

    hits = {"id": 0, "trim": 0, "trim-range": 0, "year-median": 0}
    miss = 0
    for c in d["cars"]:
        for k in ("listPrice", "listPriceBasis", "listPriceMin", "listPriceMax", "vsList"):
            c[k] = None
        y, t = c.get("year"), norm(c.get("trim"))
        lp = basis = None

        sid = c.get("subModelId")
        # year|id — a sub-model id recurs across years with a different price each year.
        # byId values may be a bare price (compact) or {price:...} (verbose) — accept both.
        e = by_id.get(f"{y}|{sid}") if (sid is not None and y) else None
        idp = e.get("price") if isinstance(e, dict) else e
        if idp:
            lp, basis = idp, "id"
        elif y:
            e = by_trim.get(f"{y}|{t}")
            if e:
                if isinstance(e, dict):
                    if e["min"] == e["max"]:
                        lp, basis = e["min"], "trim"
                    else:
                        # ambiguous: report the range, compare against its midpoint
                        lp, basis = round((e["min"] + e["max"]) / 2), "trim-range"
                        c["listPriceMin"], c["listPriceMax"] = e["min"], e["max"]
                else:
                    lp, basis = e, "trim"
            if not lp:
                ym = by_year.get(str(y)) or by_year.get(y)
                if ym:
                    lp, basis = ym["med"], "year-median"
        if not lp:
            miss += 1
            continue
        c["listPrice"], c["listPriceBasis"] = lp, basis
        if c.get("price") and c["price"] > 1000:
            c["vsList"] = round(c["price"] / lp - 1, 4)
        hits[basis] += 1

    d["priceList"] = {"source": "Yad2 מחירון (official used price list)", "fetched": plfile.get("fetched"),
                      "joinedOn": hits, "unmatched": miss, "version": 2}
    json.dump(d, open(data_path, "w", encoding="utf-8"), ensure_ascii=False)

    vs = [c["vsList"] for c in d["cars"] if c.get("vsList") is not None]
    print(f"{d['label']}: joined {hits}, unmatched {miss}")
    if vs:
        print(f"  vs list median {st.median(vs)*100:+.0f}%  range {min(vs)*100:+.0f}% .. {max(vs)*100:+.0f}%  |  5%+ under list: {sum(1 for v in vs if v < -0.05)}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
