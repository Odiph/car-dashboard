# -*- coding: utf-8 -*-
"""Build a self-contained shareable dashboard from one or more Yad2 scrape JSONs.

    python make_dashboard.py out.html data1.json [data2.json ...]

Single HTML file, data embedded, no server and no network needed — openable by anyone
you send it to, and works from a file:// path or any static host.
"""
import json, sys, os, html, statistics as st

def load(paths):
    sets = []
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        cars = [c for c in d["cars"] if not c.get("gone")]
        for c in cars:
            c["_model"] = d["label"]
        fc = d.get("feedCounts", {})
        sets.append({
            "label": d["label"], "scraped": d["scraped"], "url": d["url"],
            "private": fc.get("private", len(cars)),
            "commercial": fc.get("commercial", d.get("commercialCount", 0)),
            "total": d.get("totalListings") or 0,
            "note": d.get("note", ""),
            "cars": cars,
            # auctions are a separate MODE: never merged into `cars`
            "auctions": d.get("auctions", []),
            "auctionsMeta": d.get("auctionsMeta", {}),
        })
    return sets

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Cache-Control" content="no-cache, must-revalidate"><meta http-equiv="Pragma" content="no-cache">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#0f1420;--card:#171e2e;--line:#273349;--tx:#e8edf7;--dim:#93a1bd;--acc:#5b9cff;--good:#3ecf8e;--bad:#ff6b6b;--warn:#ffc14d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:22px}
h1{margin:0 0 4px;font-size:23px}
.sub{color:var(--dim);font-size:13px;margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi .v{font-size:25px;font-weight:650;letter-spacing:-.5px}
.kpi .l{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-top:3px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:18px}
.panel h2{margin:0 0 12px;font-size:14px;color:var(--dim);text-transform:uppercase;letter-spacing:.7px;font-weight:600}
.row{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:940px){.row{grid-template-columns:1fr}}
.bars{display:flex;flex-direction:column;gap:7px}
.bar{display:grid;grid-template-columns:110px 1fr 46px;align-items:center;gap:9px;font-size:12px}
.bar .t{color:var(--dim);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar .g{background:#1e2739;border-radius:5px;height:17px;overflow:hidden}
.bar .g div{height:100%;background:linear-gradient(90deg,var(--acc),#8f6bff);border-radius:5px}
.bar .n{text-align:right;color:var(--dim);font-variant-numeric:tabular-nums}
.ctl{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-bottom:12px}
input,select{background:#121a29;color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:13px}
input[type=range]{padding:0}
label.f{display:flex;flex-direction:column;gap:3px;font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#1b2334;cursor:pointer;user-select:none;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim);z-index:2}
th:hover{color:var(--tx)}
tbody tr:hover{background:#1d2637}
td.n{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.pill{display:inline-block;padding:1px 7px;border-radius:99px;font-size:10.5px;font-weight:600}
.g{background:rgba(62,207,142,.16);color:var(--good)}
.b{background:rgba(255,107,107,.16);color:var(--bad)}
.w{background:rgba(255,193,77,.16);color:var(--warn)}
.tw{max-height:620px;overflow:auto;border-radius:9px;border:1px solid var(--line)}
.miss{color:#6b7891;font-style:italic}
.note{background:rgba(255,193,77,.08);border-left:3px solid var(--warn);padding:11px 13px;border-radius:7px;font-size:12.5px;color:#d9c9a3;margin-bottom:18px}
.foot{color:#6b7891;font-size:11.5px;margin-top:22px;line-height:1.7}
.tabs{display:flex;gap:7px;margin-bottom:16px;flex-wrap:wrap}
.tab{background:var(--card);border:1px solid var(--line);color:var(--dim);padding:7px 15px;border-radius:9px;cursor:pointer;font-size:13px}
.tab.on{background:var(--acc);border-color:var(--acc);color:#04101f;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chip{background:#121a29;border:1px solid var(--line);color:var(--dim);padding:5px 11px;border-radius:99px;cursor:pointer;font-size:12px;user-select:none;white-space:nowrap}
.chip:hover{border-color:var(--acc);color:var(--tx)}
.chip.on{background:var(--acc);border-color:var(--acc);color:#04101f;font-weight:600}
.chip .c{opacity:.65;font-size:11px;margin-left:3px}
.chip.clr{border-style:dashed}
.stamp{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:99px;
  padding:4px 13px;font-size:11.5px;color:var(--dim);margin-bottom:14px}
.stamp b{color:var(--tx);font-weight:600}
.modes{display:flex;gap:8px;align-items:center;margin:0 0 14px}
.mode{background:var(--card);border:1px solid var(--line);color:var(--dim);padding:6px 13px;border-radius:9px;cursor:pointer;font-size:12.5px;user-select:none}
.mode.on{border-color:var(--warn);color:var(--warn);background:rgba(255,193,77,.10);font-weight:600}
.mode .c{opacity:.7;font-size:11px;margin-left:4px}
.aucnote{background:rgba(255,193,77,.08);border-left:3px solid var(--warn);padding:10px 13px;border-radius:7px;font-size:12.5px;color:#d9c9a3;margin:0 0 12px}
tr.auc td{background:rgba(255,193,77,.05)}
.tag{display:inline-block;padding:1px 6px;border-radius:5px;font-size:10px;font-weight:700;letter-spacing:.4px;background:rgba(255,193,77,.18);color:var(--warn);margin-right:5px;vertical-align:1px}
</style></head><body><div class="wrap">
<h1>__TITLE__</h1>
<div class="stamp">Last refreshed <b>__BUILT__</b> &nbsp;·&nbsp; refreshes daily at 03:00 <span id="agewarn"></span></div>
<div class="sub" id="sub"></div>
<div class="tabs" id="tabs"></div>
<div class="modes"><span style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px">Show</span>
  <div class="mode on" data-m="private">Private listings</div>
  <div class="mode" data-m="auctions" id="modeAuc">Auctions <span class="c" id="aucCount"></span></div>
</div>
<div class="aucnote" id="aucnote" style="display:none"><b>Auction lots (konesy2.co.il) are a different purchase.</b> There is no asking price — the number shown is the
<b>opening bid</b> (or the current top bid once bidding starts), and <b>headroom</b> is how far it could rise before reaching the מחירון book value: it is your ceiling, not a discount.
Almost every lot is ex-leasing / fleet, sold as-is, usually without a test drive. <span id="aucfee"></span></div>
<div class="note"><b>Before you fall for one:</b> Yad2 never publishes service history or accident history — they are not in any listing.
Get a pre-purchase inspection (בדיקת רכב) and ask the seller for the plate number (מספר רכב) so the gov.il ownership &amp; lien record can be checked.</div>
<div class="kpis" id="kpis"></div>
<div class="row">
  <div class="panel"><h2>Price distribution</h2><div class="bars" id="hist"></div></div>
  <div class="panel"><h2>Model year</h2><div class="bars" id="years"></div></div>
</div>
<div class="row">
  <div class="panel"><h2>Fuel</h2><div class="bars" id="fuel"></div></div>
  <div class="panel"><h2>Where the cars are</h2><div class="bars" id="regions"></div></div>
</div>
<div class="panel">
  <h2>Every listing</h2>
  <div class="ctl" style="margin-bottom:10px">
    <label class="f" style="width:100%">Trim <span id="tsel" style="text-transform:none;letter-spacing:0;color:var(--tx)"></span>
      <div class="chips" id="trims"></div></label>
  </div>
  <div class="ctl">
    <label class="f">Search<input id="q" placeholder="trim, city, colour..." style="width:190px"></label>
    <label class="f">Max price<input id="mx" type="range" min="0" max="100" value="100" style="width:150px"><span id="mxv" style="font-size:12px;text-transform:none;letter-spacing:0"></span></label>
    <label class="f">Max km<input id="mk" type="range" min="0" max="100" value="100" style="width:150px"><span id="mkv" style="font-size:12px;text-transform:none;letter-spacing:0"></span></label>
    <label class="f">Fuel<select id="ff"><option value="">any</option></select></label>
    <label class="f">Min year<select id="fy"><option value="">any</option></select></label>
    <label class="f">Price vs מחירון<select id="fl"><option value="">any</option><option value="-5">5%+ below</option><option value="-10">10%+ below</option><option value="0">at or below</option></select></label>
    <label class="f">Owner history<select id="fo"><option value="">any</option><option value="priv">private since new</option><option value="fleet">ex-fleet only</option></select></label>
    <label class="f">Listing age<select id="fa"><option value="">any</option><option value="7">new this week</option><option value="30">last 30 days</option><option value="stale90">stale (90d+)</option></select></label>
    <label class="f" style="justify-content:flex-end"><span style="visibility:hidden">x</span>
      <span style="display:flex;align-items:center;gap:6px;text-transform:none;letter-spacing:0;font-size:12.5px;color:var(--tx);cursor:pointer">
        <input type="checkbox" id="fp" style="width:15px;height:15px;accent-color:var(--acc);cursor:pointer">
        hide "no price"</span></label>
    <label class="f">&nbsp;<span id="cnt" style="font-size:12px;text-transform:none;letter-spacing:0;color:var(--tx)"></span></label>
  </div>
  <div class="tw"><table><thead><tr id="hd"></tr></thead><tbody id="tb"></tbody></table></div>
</div>
<div class="foot" id="foot"></div>
</div>
<script>
const SETS = __DATA__;
let cur = 0, sortKey='price', sortDir=1, trimSel = new Set();
// view mode: 'private' (Yad2 listings) or 'auctions' (konesy2 lots). Separate tables — the two
// have different price semantics and must never share a price column.
let mode = 'private';

// Trim NAME out of Yad2's long subModel string. The name is not always the first token:
// Kona prefixes drivetrain ("4X2 Premium ...", "4X4 Prestige ..."), so first-word grouping
// would yield "4X2" as a trim. Match known marketing names, and keep the FL facelift split.
const TRIM_NAMES = ['Open Sky','N Line','Panoramic','Prestige','Premium','Supreme','Classic',
  'Prime Plus','Prime','Inspire','Intense','Ultimate','Luxury','Comfort','Sense','Elite','Style','Pure','Sun']
  .sort((a,b)=>b.length-a.length);
function trimName(t){
  t = t || '';
  for(const n of TRIM_NAMES){
    if(new RegExp('(^|\\\\s)'+n.replace(/ /g,'\\\\s')+'(\\\\s|$)','i').test(t))
      return n + (/(^|\s)FL(\s|$)/.test(t) ? ' FL' : '');
  }
  return (t.split(/\s+/)[0]) || 'other';
}
const ils = n => n==null ? null : '\\u20aa'+Number(n).toLocaleString('en-US');
const num = n => n==null ? null : Number(n).toLocaleString('en-US');
const med = a => { if(!a.length) return null; const s=[...a].sort((x,y)=>x-y), m=s.length>>1;
  return s.length%2 ? s[m] : Math.round((s[m-1]+s[m])/2); };

const COLS = [
 ['year','Year',0],['trim','Trim',0],['price','Price',1],['listPrice','מחירון',1],['vsList','vs מחירון',1],
 ['hand','Hand',1],['ownerShort','Owner history',0],['ageDays','Listed',1],
 ['km','KM',1],['kmyr','KM/yr',1],['color','Colour',0],['fuel','Fuel',0],
 ['test','Test to',0],['city','City',0],['link','',0]
];

// "vs year med" = this car's asking price against the MEDIAN ASKING PRICE of the same
// model+year in this same dataset. Computed from real listings here — Yad2's own
// `abovePrice` field is NOT a valuation (it is a coarse search bucket: only 2-4 distinct
// values across hundreds of cars) and must never be used for this.
function cars(){
  const all = SETS[cur].cars;
  const byYear = {};
  all.forEach(c=>{ if(c.price && c.year){ (byYear[c.year]=byYear[c.year]||[]).push(c.price); } });
  const medByYear = {};
  for(const y in byYear) medByYear[y] = med(byYear[y]);
  const TODAY = new Date(SETS[cur].scraped + 'T12:00:00');
  // owner = Yad2's בעלות מקורית (ORIGINAL ownership). 'פרטית' means private since new;
  // anything else means the car was fleet/lease/rental before, even though a private
  // person is selling it now. This is the ex-fleet signal, and it is not the same thing
  // as the seller being private.
  const OWN = {'פרטית':'private since new','חברה':'ex-company','החכר (ליסינג)':'ex-leasing',
               'ליסינג':'ex-leasing','השכרה':'ex-rental','מונית':'ex-taxi','לימוד נהיגה':'ex-driving school'};
  return all.map(c=>{
    const m = (c.price && c.year && byYear[c.year] && byYear[c.year].length>=3) ? medByYear[c.year] : null;
    let ageDays = null;
    if(c.posted){ const d=new Date(c.posted+'T12:00:00');
      if(!isNaN(d)) ageDays = Math.max(0, Math.round((TODAY-d)/864e5)); }
    // days until the roadworthiness test (טסט) expires — negative means already lapsed
    let testDays = null;
    if(c.test){ const d=new Date(c.test+'T12:00:00');
      if(!isNaN(d)) testDays = Math.round((d-TODAY)/864e5); }
    return {...c, yearMed: m, vs: m ? (c.price/m - 1) : null, tname: trimName(c.trim),
            ageDays, testDays,
            ownerShort: OWN[c.owner] || c.owner || null,
            exFleet: !!(c.owner && c.owner !== 'פרטית') };
  });
}

function renderTrims(){
  const cs = cars(), counts = {};
  cs.forEach(c=>{ counts[c.tname] = (counts[c.tname]||0)+1; });
  const names = Object.keys(counts).sort((a,b)=>counts[b]-counts[a]);
  // drop selections that don't exist in this model
  [...trimSel].forEach(t=>{ if(!counts[t]) trimSel.delete(t); });
  const el = document.getElementById('trims');
  el.innerHTML = names.map(n=>
    `<div class="chip ${trimSel.has(n)?'on':''}" data-t="${html(n)}">${html(n)}<span class="c">${counts[n]}</span></div>`
  ).join('') + (trimSel.size ? `<div class="chip clr" data-clear="1">clear</div>` : '');
  el.querySelectorAll('.chip').forEach(ch=>ch.addEventListener('click',()=>{
    if(ch.dataset.clear){ trimSel.clear(); }
    else { const t=ch.dataset.t; trimSel.has(t) ? trimSel.delete(t) : trimSel.add(t); }
    renderTrims(); renderTable();
  }));
  document.getElementById('tsel').textContent =
    trimSel.size ? `— ${trimSel.size} selected` : '— all (click to filter, pick several)';
}

function bars(el, pairs, fmt){
  const mx = Math.max(...pairs.map(p=>p[1]), 1);
  el.innerHTML = pairs.map(([k,v])=>
   `<div class="bar"><div class="t">${html(k)}</div><div class="g"><div style="width:${v/mx*100}%"></div></div><div class="n">${fmt?fmt(v):v}</div></div>`).join('');
}
function html(s){ return String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }

// ---------------- AUCTIONS MODE ----------------
const AUC_COLS = [
 ['year','Year',1],['trim','Trim',0],['bidRef','Bid',1],['listPrice','מחירון',1],['headroomVsList','Headroom',1],
 ['estAllIn','Est. all-in',1],['daysToAuction','Auction',1],['km','KM',1],['hand','Hand',1],['ownership','Owner history',0],
 ['condition','Condition',0],['sellerType','Seller',0],['link','',0]
];
const OWN_A = {'ליסינג':'ex-leasing','פרטית':'private','פרטי':'private','חברה':'ex-company','השכרה':'ex-rental','מונית':'ex-taxi'};
function aucs(){ return (SETS[cur].auctions||[]).map(a=>({...a})); }
function renderAuctions(){
  const S=SETS[cur], as=aucs(), meta=S.auctionsMeta||{};
  document.getElementById('aucCount').textContent = as.length ? `(${as.length})` : '(0)';
  document.getElementById('aucfee').innerHTML = meta.feePctAssumed!=null
    ? `<b>Est. all-in</b> adds an <b>assumed ${Math.round(meta.feePctAssumed*100)}% buyer fee</b> — konesy2 does not publish its fee; treat it as a placeholder until you have their rate card.` : '';
  document.getElementById('hd').innerHTML = AUC_COLS.map(([k,l,n])=>`<th data-k="${k}" class="${n?'n':''}">${l}</th>`).join('');
  document.querySelectorAll('#hd th').forEach(th=>th.onclick=()=>{ const k=th.dataset.k; if(k==='link')return;
    sortDir=(sortKey===k)?-sortDir:1; sortKey=k; renderAuctions(); });
  if(!AUC_COLS.some(c=>c[0]===sortKey)) { sortKey='daysToAuction'; sortDir=1; }
  const q=document.getElementById('q').value.toLowerCase().trim();
  let rows=as.filter(a=>!q || [a.trim,a.title,a.ownership,a.condition,a.sellerType].some(v=>String(v||'').toLowerCase().includes(q)));
  rows.sort((a,b)=>{ let x=a[sortKey],y=b[sortKey]; if(x==null)return 1; if(y==null)return -1;
    if(typeof x==='string')return sortDir*x.localeCompare(y); return sortDir*(x-y); });
  document.getElementById('cnt').textContent=rows.length+' lots';
  document.getElementById('tb').innerHTML = rows.map(a=>{
    const bid = a.bidRef ? `${ils(a.bidRef)} <span class="miss" style="font-size:10.5px">${a.bidKind==='top'?'top bid':'opening'}</span>`
                         : '<span class="miss">sealed bid — no price published</span>';
    const hr = a.headroomVsList==null ? '<span class="miss">&mdash;</span>'
             : `<span class="pill ${a.headroomVsList>0.15?'g':(a.headroomVsList<0?'b':'w')}" title="how far the bid could rise before reaching book value — your ceiling, not a discount">${(a.headroomVsList*100).toFixed(0)}%</span>`;
    const LPB={'trim':'matched on trim','trim-range':'several list values under this trim; midpoint','year-median':'trim not in list — year median (*)'};
    const lp = a.listPrice==null ? '<span class="miss">&mdash;</span>' : `<span title="${LPB[a.listPriceBasis]||''}">${ils(a.listPrice)}${a.listPriceBasis==='year-median'?'*':(a.listPriceBasis==='trim-range'?'~':'')}</span>`;
    const dd = a.daysToAuction==null ? '<span class="miss">&mdash;</span>'
             : (a.status==='closed' ? `<span class="pill b">closed</span>` : a.status==='live' ? `<span class="pill g">LIVE now</span>`
             : `<span class="pill ${a.daysToAuction<=2?'w':''}" title="${html(a.auctionAt||'')}">${a.daysToAuction<1?'today':'in '+Math.ceil(a.daysToAuction)+'d'}</span> <span class="miss" style="font-size:10.5px">${html((a.auctionAt||'').slice(0,5))}</span>`);
    const own = !a.ownership ? '<span class="miss">&mdash;</span>' : (/פרטי/.test(a.ownership) ? `<span style="color:var(--dim)">${OWN_A[a.ownership]||a.ownership}</span>` : `<span class="pill w">${OWN_A[a.ownership]||html(a.ownership)}</span>`);
    return `<tr class="auc">
      <td class="n">${a.year||''}</td>
      <td title="${html(a.title)}"><span class="tag">AUCTION</span>${html(a.trim||a.title||'')}</td>
      <td class="n">${bid}</td>
      <td class="n">${lp}</td>
      <td class="n">${hr}</td>
      <td class="n">${a.estAllIn?ils(a.estAllIn):'<span class="miss">&mdash;</span>'}</td>
      <td class="n">${dd}</td>
      <td class="n">${a.km?num(a.km):'<span class="miss">&mdash;</span>'}</td>
      <td class="n">${a.hand??''}</td>
      <td>${own}</td>
      <td>${html(a.condition||'')}</td>
      <td>${html(a.sellerType||'')}</td>
      <td><a href="${html(a.url)}" target="_blank">open &rarr;</a></td></tr>`; }).join('');
}
function applyMode(){
  const auc = mode==='auctions';
  document.querySelectorAll('.mode').forEach(m=>m.classList.toggle('on', m.dataset.m===mode));
  document.getElementById('aucnote').style.display = auc ? '' : 'none';
  // private-only controls have no meaning for auctions; hide them rather than let them silently no-op
  ['mx','mk','ff','fy','fl','fo','fa','fp'].forEach(id=>{ const el=document.getElementById(id); const lab=el.closest('label'); if(lab) lab.style.display = auc?'none':''; });
  document.getElementById('trims').closest('.ctl').style.display = auc?'none':'';
  if(auc) renderAuctions(); else { document.getElementById('hd').innerHTML = COLS.map(([k,l,n])=>`<th data-k="${k}" class="${n?'n':''}">${l}</th>`).join('');
    document.querySelectorAll('#hd th').forEach(th=>th.onclick=()=>{ const k=th.dataset.k; if(k==='link')return; sortDir=(sortKey===k)?-sortDir:1; sortKey=k; renderTable(); });
    if(!COLS.some(c=>c[0]===sortKey)) { sortKey='price'; sortDir=1; } renderTable(); }
}
document.querySelectorAll('.mode').forEach(m=>m.onclick=()=>{ mode=m.dataset.m; applyMode(); });

function renderTop(){
  const S=SETS[cur], cs=cars(), pr=cs.map(c=>c.price).filter(Boolean), km=cs.map(c=>c.kmyr).filter(Boolean);
  document.getElementById('aucCount').textContent = `(${(S.auctions||[]).length})`;
  document.getElementById('sub').innerHTML =
    `Yad2, scraped ${S.scraped} &middot; <b>${S.private}</b> private sellers of ${S.total} total listings `+
    `(${Math.round(S.private/S.total*100)}%) &middot; ${S.commercial} dealer/leasing listings excluded`+
    (S.note?` &middot; ${html(S.note)}`:'');
  const share = Math.round(S.private/S.total*100);
  document.getElementById('kpis').innerHTML = [
    ['Private listings', S.private],
    ['Private share', share+'%'],
    ['Cheapest', ils(Math.min(...pr))],
    ['Median price', ils(med(pr))],
    ['Dearest', ils(Math.max(...pr))],
    ['Median km/yr', num(med(km))],
    ['5%+ below מחירון', cs.filter(c=>c.vsList!=null && c.vsList<=-0.05).length],
  ].map(([l,v])=>`<div class="kpi"><div class="v">${v==null?'&mdash;':v}</div><div class="l">${l}</div></div>`).join('');

  // price histogram
  const lo=Math.min(...pr), hi=Math.max(...pr), B=8, w=(hi-lo)/B||1, bk=Array(B).fill(0);
  pr.forEach(p=>{ let i=Math.floor((p-lo)/w); if(i>=B)i=B-1; bk[i]++; });
  bars(document.getElementById('hist'), bk.map((n,i)=>
    [ils(Math.round(lo+i*w))+'+', n]));

  const cnt=(key)=>{ const m={}; cs.forEach(c=>{ const k=c[key]||'unknown'; m[k]=(m[k]||0)+1; }); return m; };
  const yrs=cnt('year');
  bars(document.getElementById('years'), Object.keys(yrs).sort().map(k=>[k,yrs[k]]));
  const fu=cnt('fuel');
  bars(document.getElementById('fuel'), Object.entries(fu).sort((a,b)=>b[1]-a[1]));
  const rg=cnt('region');
  bars(document.getElementById('regions'), Object.entries(rg).sort((a,b)=>b[1]-a[1]).slice(0,9));

  // filter controls
  const ff=document.getElementById('ff'), fy=document.getElementById('fy');
  ff.innerHTML='<option value="">any</option>'+Object.keys(fu).sort().map(k=>`<option>${html(k)}</option>`).join('');
  fy.innerHTML='<option value="">any</option>'+Object.keys(yrs).sort().map(k=>`<option>${k}</option>`).join('');
  const mx=document.getElementById('mx'), mk=document.getElementById('mk');
  mx.min=Math.floor(lo); mx.max=Math.ceil(hi); mx.value=mx.max;
  const kmax=Math.max(...cs.map(c=>c.km||0)); mk.min=0; mk.max=kmax; mk.value=kmax;
  document.getElementById('hd').innerHTML = COLS.map(([k,l,n])=>`<th data-k="${k}" class="${n?'n':''}">${l}</th>`).join('');
  document.querySelectorAll('#hd th').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(k==='link')return;
    sortDir = (sortKey===k) ? -sortDir : 1; sortKey=k; renderTable(); });
  document.getElementById('foot').innerHTML =
    `Source: <a href="${html(S.url)}" target="_blank">Yad2 listing search</a>. Seller type is Yad2's own <code>adType</code> field, not inferred. `+
    `All prices are ASKING prices. <b>מחירון</b> is Yad2's own official used-car price list for that exact `+
    `year + trim (an asterisk means the trim was absent and the year's median was used), and <b>vs מחירון</b> `+
    `is the asking price against it &mdash; green = below list, red = above. `+
    `It is a book valuation: it cannot see condition, accident history or options, so a car far below list `+
    `is either a bargain or has a reason. `+
    `Trim chips are multi-select. Click any column header to sort. `+
    `Listings change daily &mdash; treat this as a ${S.scraped} snapshot.`;
  renderTrims();
  renderTable();
}

function renderTable(){
  const q=document.getElementById('q').value.toLowerCase().trim();
  const mx=+document.getElementById('mx').value, mk=+document.getElementById('mk').value;
  const ff=document.getElementById('ff').value, fy=document.getElementById('fy').value;
  const fl=document.getElementById('fl').value;
  const fo=document.getElementById('fo').value, fa=document.getElementById('fa').value;
  // "no price" = seller wrote לא צוין מחיר. Also treat a 0/absurd price as unpriced:
  // one Yad2 listing genuinely carries price 0, which would otherwise sort to the top.
  const fp=document.getElementById('fp').checked;
  const priced = c => c.price != null && c.price > 1000;
  const ownOk = c => fo==='priv' ? (c.ownerShort && !c.exFleet) : (fo==='fleet' ? c.exFleet : true);
  const ageOk = c => {
    if(!fa) return true;
    if(c.ageDays==null) return false;
    if(fa==='stale90') return c.ageDays>90;
    return c.ageDays <= +fa;
  };
  document.getElementById('mxv').textContent=ils(mx);
  document.getElementById('mkv').textContent=num(mk)+' km';
  let rows=cars().filter(c=>
    (!q || [c.trim,c.city,c.color,c.fuel,c.region].some(v=>String(v||'').toLowerCase().includes(q))) &&
    (c.price==null || c.price<=mx) && (c.km==null || c.km<=mk) &&
    (!ff || c.fuel===ff) && (!fy || c.year>=+fy) &&
    (trimSel.size===0 || trimSel.has(c.tname)) &&
    (!fl || (c.vsList!=null && c.vsList <= +fl/100)) &&
    ownOk(c) && ageOk(c) && (!fp || priced(c)));
  rows.sort((a,b)=>{ let x=a[sortKey],y=b[sortKey];
    if(x==null)return 1; if(y==null)return -1;
    if(typeof x==='string')return sortDir*x.localeCompare(y);
    return sortDir*(x-y); });
  const kms=rows.map(c=>c.kmyr).filter(Boolean), m=med(kms);
  document.getElementById('cnt').textContent=rows.length+' shown';
  document.getElementById('tb').innerHTML = rows.map(c=>{
    const vs = c.vs==null ? '<span class="miss">&mdash;</span>'
      : `<span class="pill ${c.vs<-0.03?'g':(c.vs>0.03?'b':'w')}">${(c.vs*100).toFixed(0)}%</span>`;
    const ky = c.kmyr==null ? '<span class="miss">&mdash;</span>'
      : (m && c.kmyr<m*0.7 ? `<span class="pill g">${num(c.kmyr)}</span>`
        : (m && c.kmyr>m*1.4 ? `<span class="pill b">${num(c.kmyr)}</span>` : num(c.kmyr)));
    const vl = c.vsList==null ? '<span class="miss">&mdash;</span>'
      : `<span class="pill ${c.vsList<-0.03?'g':(c.vsList>0.03?'b':'w')}">${(c.vsList*100).toFixed(0)}%</span>`;
    // ex-fleet is the thing to notice; "private since new" is the unremarkable default
    const own = !c.ownerShort ? '<span class="miss">&mdash;</span>'
      : (c.exFleet ? `<span class="pill w">${html(c.ownerShort)}</span>`
                   : `<span style="color:var(--dim)">${html(c.ownerShort)}</span>`);
    // a listing sitting unsold for months is either overpriced or has a problem — leverage
    const age = c.ageDays==null ? '<span class="miss">&mdash;</span>'
      : (c.ageDays>180 ? `<span class="pill b" title="listed ${c.ageDays} days — unsold for 6+ months">${c.ageDays}d</span>`
      : (c.ageDays>90  ? `<span class="pill w" title="listed ${c.ageDays} days">${c.ageDays}d</span>`
      : `${c.ageDays}d`));
    // טסט expiry: a test due soon is a real cost to fold into the offer
    const tst = !c.test ? '<span class="miss">&mdash;</span>'
      : (c.testDays!=null && c.testDays<0  ? `<span class="pill b" title="test LAPSED ${-c.testDays} days ago">${c.test}</span>`
      : (c.testDays!=null && c.testDays<=60 ? `<span class="pill w" title="test due in ${c.testDays} days">${c.test}</span>`
      : html(c.test)));
    const LPB = {'id':'exact match on Yad2 sub-model id', 'trim':'matched on trim name',
                 'trim-range':`Yad2 lists ${ils(c.listPriceMin)}–${ils(c.listPriceMax)} under this trim name; midpoint shown`,
                 'year-median':'trim not in the price list — median of the year shown'};
    const lp = c.listPrice==null ? '<span class="miss">&mdash;</span>'
      : `<span title="${LPB[c.listPriceBasis]||''}">${ils(c.listPrice)}${c.listPriceBasis==='year-median'?'*':(c.listPriceBasis==='trim-range'?'~':'')}</span>`;
    return `<tr>
      <td class="n">${c.year||''}</td>
      <td title="${html(c.trim)}">${html(String(c.trim||'').slice(0,34))}</td>
      <td class="n">${(c.price&&c.price>1000)?ils(c.price):'<span class="miss">no price</span>'}</td>
      <td class="n">${lp}</td>
      <td class="n">${vl}</td>
      <td class="n">${c.hand??''}</td>
      <td>${own}</td>
      <td class="n">${age}</td>
      <td class="n">${c.km?num(c.km):'<span class="miss">&mdash;</span>'}</td>
      <td class="n">${ky}</td>
      <td>${html(c.color||'')}</td>
      <td>${html(c.fuel||'')}</td>
      <td>${tst}</td>
      <td>${html(c.city||'')}</td>
      <td><a href="https://www.yad2.co.il/vehicles/item/${c.id}" target="_blank">open &rarr;</a></td></tr>`;
  }).join('');
}

document.getElementById('tabs').innerHTML = SETS.map((s,i)=>
  `<div class="tab ${i===0?'on':''}" data-i="${i}">${html(s.label)} <span style="opacity:.6">${s.private}</span></div>`).join('');
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  cur=+t.dataset.i;
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));
  document.getElementById('q').value='';
  trimSel.clear();
  renderTop();
  applyMode();   // keep the chosen mode (private/auctions) when switching model
});
// If the scheduled refresh dies, the page must SAY it is stale rather than look current.
(function(){
  const built = new Date("__BUILT_ISO__");
  if(isNaN(built)) return;
  const days = Math.floor((Date.now()-built)/864e5);
  if(days >= 2) document.getElementById('agewarn').innerHTML =
    ` &nbsp;·&nbsp; <span style="color:var(--bad);font-weight:600">⚠ ${days} days old — the daily refresh may have stopped</span>`;
})();

['q','mx','mk','ff','fy','fl','fo','fa','fp'].forEach(id=>{
  const e=document.getElementById(id);
  // bind BOTH: selects and checkboxes emit 'change', text/range emit 'input'
  e.addEventListener('change', renderTable);
  if(e.tagName==='INPUT' && e.type!=='checkbox') e.addEventListener('input', renderTable); });
renderTop();
</script></body></html>
"""

if __name__ == "__main__":
    import datetime as _dt
    out, srcs = sys.argv[1], sys.argv[2:]
    sets = load(srcs)
    title = " vs ".join(s["label"] for s in sets) + " — private sellers, Israel"
    now = _dt.datetime.now().astimezone()
    page = (PAGE.replace("__DATA__", json.dumps(sets, ensure_ascii=False))
                .replace("__TITLE__", html.escape(title))
                .replace("__BUILT_ISO__", now.isoformat())
                .replace("__BUILT__", now.strftime("%a %d %b %Y, %H:%M")))
    open(out, "w", encoding="utf-8").write(page)
    print("SAVED:", out)
    print("size:", round(len(page) / 1024), "KB")
    for s in sets:
        print(f"  {s['label']}: {len(s['cars'])} cars")
