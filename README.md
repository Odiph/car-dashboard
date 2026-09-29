# car-dashboard

Private-seller used-car market dashboard for Israel (Hyundai Kona + Hyundai Ioniq hybrid), rebuilt nightly.

- **Live:** https://odiph.github.io/car-dashboard/ (`index.html`, self-contained, data embedded)
- **Pipeline:** `pipeline/` — scrapers (Yad2 listings, Yad2 מחירון price list, konesy2 auctions),
  join scripts, the Excel writer and the dashboard generator. **Read `pipeline/REFRESH.md` first** —
  it records every hard-won rule (seller classification, price-list join keys, pacing limits,
  auction status/price traps) and the gates a refresh must pass before anything is published.
- **Refresh:** a scheduled task runs the pipeline at 03:00 daily and pushes `index.html` here.

Sources: Yad2 (listings + official price list), konesy2.co.il (receiver/repossession auctions, shown as a
separate mode). ad.co.il is scripted but not wired in. Facebook Marketplace is deliberately excluded.
