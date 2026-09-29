# -*- coding: utf-8 -*-
"""Yad2 private-seller JSON -> formatted .xlsx.   python yad2_xlsx.py data.json [out.xlsx]

v2 (2026-09-25): consumes the __NEXT_DATA__-based scrape (adType-classified). Fields arrive
already-typed and mostly English, so there is no Hebrew regex translation layer any more.
"""
import json, sys, os, re, statistics, statistics as st
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L

MISS = "missing detail"
HE = {"פרטית": "private", "חברה": "company", "ליסינג": "leasing", "השכרה": "rental",
      "מונית": "taxi", "לימוד נהיגה": "driving school", "פנאי-שטח": "SUV / crossover",
      "מנהלים": "executive", "משפחתי": "family", "עירוני": "city", "מיני": "mini",
      "סטיישן": "estate", "מסחרי": "commercial", "בעירה פנימית": "combustion"}
def tr(v):
    if v is None or v == "": return None
    v = str(v).strip()
    return f"{v} ({HE[v]})" if v in HE else v

def build(data, out_path):
    cars = data["cars"]
    live = [c for c in cars if not c.get("gone")]
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Private sellers"

    # peer median per model-year, from real asking prices in this dataset.
    # NOTE: Yad2's `abovePrice` is NOT a valuation (coarse search bucket, 2-4 distinct
    # values across hundreds of cars) — never use it for a price comparison.
    _by = {}
    for c in live:
        if c.get("price") and c.get("year"):
            _by.setdefault(c["year"], []).append(c["price"])
    YEARMED = {y: st.median(v) for y, v in _by.items() if len(v) >= 3}

    HEAD = ["Year", "Model / trim", "Price (ILS)", "מחירון (list)", "vs מחירון", "Hand", "KM",
            "KM / year", "Color", "Previously leased?", "Dealer?", "Service history", "Accidents",
            "Test valid to", "Gearbox", "Fuel", "Drive", "HP", "Safety /8", "City", "Listed", "Link"]

    ws["A1"] = f"{data['label']} — private sellers only — Yad2, {data['scraped']}"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(HEAD))

    fc = data.get("feedCounts", {})
    pc, cc = fc.get("private", len(live)), fc.get("commercial", data.get("commercialCount", 0))
    tot = data.get("totalListings") or (pc + cc)
    share = round(pc / tot * 100) if tot else "?"
    ws["A2"] = (f"{pc} private of {tot} total listings ({share}%); {cc} dealer/leasing excluded. "
                f"Seller type comes from Yad2's own adType field, not inferred. "
                "Service history and accident history are NOT published on Yad2 for any listing — they need a "
                "pre-purchase inspection (בדיקת רכב) plus the gov.il record, which requires the plate number.")
    ws["A2"].font = Font(italic=True, size=9, color="555555")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(HEAD))
    ws.row_dimensions[2].height = 30

    H = 4
    thin = Side(style="thin", color="BFBFBF"); bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c, h in enumerate(HEAD, 1):
        x = ws.cell(H, c, h)
        x.font = Font(bold=True, color="FFFFFF", size=10)
        x.fill = PatternFill("solid", fgColor="1F3864")
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); x.border = bd
    ws.row_dimensions[H].height = 30

    miss = PatternFill("solid", fgColor="FFF2CC"); alt = PatternFill("solid", fgColor="F7F9FC")
    GOOD, BAD = Font(size=10, color="1E6B34", bold=True), Font(size=10, color="9C0006", bold=True)

    kms = [c["kmyr"] for c in live if c.get("kmyr")]
    med = statistics.median(kms) if kms else None

    r = H + 1
    for i, c in enumerate(cars):
        price = c.get("price")
        # Prefer the official מחירון (year+trim). Fall back to peer median only if absent.
        mkt = c.get("listPrice") or YEARMED.get(c.get("year"))
        vs = c.get("vsList")
        if vs is None and price and mkt:
            vs = round(price / mkt - 1, 4)
        owner = c.get("owner") or ""
        leased = "No — private since new" if owner == "פרטית" else (tr(owner) or MISS)
        if c.get("gone"): leased = "listing removed"
        vals = [c.get("year"), c.get("trim") or MISS, price or MISS, mkt or MISS, vs, c.get("hand"),
                c.get("km") or MISS, c.get("kmyr"), (c.get("color") or MISS), leased,
                "No — private seller", MISS, MISS, c.get("test") or MISS, c.get("gear") or MISS,
                c.get("fuel") or MISS, c.get("drive") or MISS, c.get("hp"), c.get("safety"),
                c.get("city") or MISS, c.get("posted") or MISS, "Open listing"]
        for cc_, v in enumerate(vals, 1):
            x = ws.cell(r, cc_, v); x.border = bd; x.font = Font(size=10)
            if i % 2: x.fill = alt
            if v == MISS or v == "listing removed":
                x.fill = miss; x.font = Font(size=10, italic=True, color="7F6000")
        for col in (3, 4, 7): ws.cell(r, col).number_format = '#,##0'
        ws.cell(r, 5).number_format = '0%'
        if vs is not None:
            ws.cell(r, 5).font = GOOD if vs < -0.05 else (BAD if vs > 0.05 else Font(size=10))
        if c.get("kmyr") and med and c["kmyr"] < med * 0.7: ws.cell(r, 8).font = GOOD
        if c.get("kmyr") and med and c["kmyr"] > med * 1.4: ws.cell(r, 8).font = BAD
        lk = ws.cell(r, len(HEAD))
        lk.hyperlink = f"https://www.yad2.co.il/vehicles/item/{c['id']}"
        lk.font = Font(size=10, color="0563C1", underline="single")
        r += 1

    ws.auto_filter.ref = f"A{H}:{L(len(HEAD))}{r-1}"
    ws.freeze_panes = ws.cell(H + 1, 3)
    for cc_, w in enumerate([7, 32, 15, 15, 10, 7, 15, 11, 15, 24, 19, 17, 16, 16, 15, 16, 15, 7, 10, 18, 15, 13], 1):
        ws.column_dimensions[L(cc_)].width = w

    n = wb.create_sheet("Notes & method")
    rows = [
        ("Source", data["url"]), ("Scraped", data["scraped"]),
        ("Total listings", tot), ("Private", pc), ("Dealer / leasing", cc),
        ("Private share", f"{share}%"), ("Pages scanned", data.get("pages")),
        ("Seller classification", "Yad2's own `adType` field ('private' / 'commercial') from the page's embedded JSON. NOT inferred from CSS classes or seller names."),
        ("", ""),
        ("Always 'missing detail'", ""),
        ("Service history", "Not published on Yad2 for ANY listing. Needs a pre-purchase inspection (בדיקת רכב)."),
        ("Accidents", "Not published on Yad2 for ANY listing. Needs inspection + the gov.il record."),
        ("gov.il / liens", "Keyed on the plate number (מספר רכב); ads never show plates. Ask the seller, then look it up."),
        ("", ""),
        ("Reading the data", ""),
        ("מחירון (list)", "Yad2's OFFICIAL used-car price list value for that exact year + trim, from /price-list/feed. A real book valuation, matched on the same trim string the listing uses. Where the exact trim was absent from the list, that year's median list value is used instead."),
        ("vs מחירון", "Asking price against the מחירון value. Green = 5%+ below list, red = 5%+ above. A book valuation cannot see condition, accident history or options — a car far below list is either a bargain or has a reason."),
        ("NOT a valuation", "Yad2's `abovePrice` field looked like a valuation but is a coarse search/financing bucket — only 2-4 distinct values (50000/100000) across hundreds of cars. It was used as 'vs market' until 2026-09-25 and produced meaningless percentages. Never use it."),
        ("KM / year", "KM over age from production date. Israeli average ~15,000-17,000 km/yr. Green = under 70% of this set's median, red = over 140%."),
        ("Previously leased?", "From Yad2's owner field. 'פרטית' = private since new, never leased/rental/company."),
        ("Listing removed", "Ad 404'd between the feed scan and the detail fetch — sold or pulled mid-run."),
        ("", ""),
        ("Not covered", "Facebook Marketplace is a separate pass."),
        ("v1 bug (fixed 2026-09-25)", "v1 classified sellers by CSS class, which only exists on the ~17 server-rendered rows per page. It found 22 of 131 private Konas and reported private sellers as 7% of the market instead of 42%."),
    ]
    n["A1"] = f"{data['label']} — method & caveats"; n["A1"].font = Font(bold=True, size=13)
    rr = 3
    for k, v in rows:
        a = n.cell(rr, 1, k); b = n.cell(rr, 2, v if v != "" else None)
        if v == "": a.font = Font(bold=True, size=11, color="1F3864")
        else:
            a.font = Font(bold=True, size=10); b.font = Font(size=10)
            b.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    n.column_dimensions["A"].width = 28; n.column_dimensions["B"].width = 100

    wb.save(out_path)
    return out_path, len(cars), len(live)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    slug = re.sub(r"[^A-Za-z0-9]+", "-", data["label"]).strip("-")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.expanduser("~"), "Downloads", f"{slug}-private-sellers-{data['scraped']}.xlsx")
    p, n, live = build(data, out)
    print("SAVED:", p); print("rows:", n, "live:", live)
