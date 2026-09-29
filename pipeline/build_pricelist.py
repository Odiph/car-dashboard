# -*- coding: utf-8 -*-
"""Rebuild yad2_pricelist.json from the byYearTrim maps captured in the browser.

The maps are passed as a JSON file produced by the console fetch; this script only
recomputes byYear aggregates so the merge step has consistent input.
"""
import json, sys

def by_year(by_trim):
    buckets = {}
    for k, v in by_trim.items():
        y = k.split("|", 1)[0]
        buckets.setdefault(y, []).append(v)
    out = {}
    for y, ps in buckets.items():
        ps.sort()
        out[y] = {"min": ps[0], "max": ps[-1], "med": ps[len(ps) // 2], "n": len(ps)}
    return out

def main(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    out = {"source": "Yad2 מחירון (official used price list)", "fetched": d["fetched"]}
    for key in ("kona", "ioniq"):
        bt = d[key]["byYearTrim"]
        out[key] = {"byYearTrim": bt, "byYear": by_year(bt)}
        print(f"{key}: {len(bt)} trim entries, {len(out[key]['byYear'])} years")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print("wrote", dst)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
