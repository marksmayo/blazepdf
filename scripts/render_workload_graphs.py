#!/usr/bin/env python3
"""Render one comparison card for every workload/document benchmark case."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path


def sample_count_label(data: dict) -> str:
    """Describe actual successful-row repeats, including merged-run variation."""
    counts = {
        len(item["samples_ms"]) if "samples_ms" in item else data.get("repeats", 0)
        for item in data["measurements"] if item.get("status") == "ok"
    }
    counts.discard(0)
    if not counts:
        return "no successful measured runs"
    low, high = min(counts), max(counts)
    if low == high:
        return f"{low} measured runs per case"
    return f"{low} to {high} measured runs per case (mixed sample counts)"


def benchmark_cards(data: dict) -> list[tuple[str, str]]:
    """Return every measured benchmark case in a deterministic order."""
    return sorted({(item["work"], item["document"]) for item in data["measurements"]})


def medal_counts(data: dict) -> dict[str, dict[str, int]]:
    """Award every distinct product placement per card from successful medians.

    Ties receive the same medal and use competition ranking: 1, 1, 3.
    """
    products = {item.get("product", item["name"]) for item in data["readers"]}
    products.update(item["name"] for item in data.get("catalog", []))
    placement_keys = ["gold", "silver", "bronze", "fourth", "fifth", "sixth"]
    placement_keys.extend(f"place_{place}" for place in range(7, len(products) + 1))
    counts = {product: dict.fromkeys(placement_keys, 0) for product in products}
    for work, document in benchmark_cards(data):
        best_by_product: dict[str, float] = {}
        for item in data["measurements"]:
            if item["status"] != "ok" or item["work"] != work or item["document"] != document:
                continue
            product = item.get("product", item["reader"])
            best_by_product[product] = min(best_by_product.get(product, float("inf")), item["median_ms"])
        ranked = sorted(best_by_product.items(), key=lambda item: item[1])
        previous_time: float | None = None
        placement = 0
        for index, (product, time) in enumerate(ranked, start=1):
            if time != previous_time:
                placement = index
                previous_time = time
            medal = {
                1: "gold",
                2: "silver",
                3: "bronze",
                4: "fourth",
                5: "fifth",
                6: "sixth",
            }.get(placement, f"place_{placement}")
            if medal in counts[product]:
                counts[product][medal] += 1
    return counts


def placement_grid(data: dict) -> dict[str, dict[str, int | None]]:
    """Return each product's rank for every document/workload card."""
    products = {item.get("product", item["name"]) for item in data["readers"]}
    products.update(item["name"] for item in data.get("catalog", []))
    grid = {product: {} for product in products}
    for index, (work, document) in enumerate(benchmark_cards(data)):
        best: dict[str, float] = {}
        for item in data["measurements"]:
            if item["status"] != "ok" or item["work"] != work or item["document"] != document:
                continue
            product = item.get("product", item["reader"])
            best[product] = min(best.get(product, float("inf")), item["median_ms"])
        ranked = sorted(best.items(), key=lambda item: item[1])
        previous: float | None = None
        placement = 0
        for position, (product, value) in enumerate(ranked, start=1):
            if value != previous:
                placement = position
                previous = value
            grid[product][f"card_{index}"] = placement
    return grid


def render(data: dict) -> str:
    payload_data = dict(data)
    payload_data["sample_count_label"] = sample_count_label(data)
    payload_data["benchmark_cards"] = [
        {"work": work, "document": document} for work, document in benchmark_cards(data)
    ]
    payload_data["medal_counts"] = medal_counts(data)
    payload_data["placement_grid"] = placement_grid(data)
    payload_data["readers"] = list(data["readers"]) + [
        {"name": item["name"], "product": item["name"], "catalog_only": True}
        for item in data.get("catalog", [])
        if item["name"] not in {reader.get("product", reader["name"]) for reader in data["readers"]}
    ]
    product_count = len({item.get("product", item["name"]) for item in data["readers"]} | {item["name"] for item in data.get("catalog", [])})
    payload_data["placement_columns"] = [
        {"key": ("gold", "silver", "bronze", "fourth", "fifth", "sixth")[place - 1]
              if place <= 6 else f"place_{place}",
         "label": ("Gold", "Silver", "Bronze", "4th", "5th", "6th")[place - 1]
                  if place <= 6 else f"{place}{'th' if 10 <= place % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(place % 10, 'th')}"}
        for place in range(1, product_count + 1)
    ]
    payload = json.dumps(payload_data, separators=(",", ":")).replace("<", "\\u003c")
    page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BlazePDF benchmark graphs</title><style>
:root{--ink:#11253f;--muted:#64748b;--line:#dce4ef;--paper:#f4f7fb;--blue:#2867d8;--green:#078a70}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px system-ui}header{padding:42px max(22px,calc((100% - 1700px)/2));color:#fff;background:linear-gradient(125deg,#0d2038,#24579c)}h1{margin:0;font-size:38px}header p{color:#c9d9ee}main{max-width:none;margin:0;padding:25px clamp(14px,2vw,36px) 60px}.note{background:#e9f1ff;border-left:4px solid var(--blue);padding:13px 16px;border-radius:6px;color:#345174}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:18px}.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:17px}.card h2{font-size:16px;margin:0 0 5px}.card p{margin:0 0 14px;color:var(--muted);font-size:12px}.row{display:grid;grid-template-columns:135px 1fr 135px;gap:9px;align-items:center;margin:9px 0;font-size:12px}.track{height:13px;background:#e8eef7;border-radius:8px;overflow:hidden}.fill{height:100%;background:#94b6ec;border-radius:8px}.winner .fill{background:linear-gradient(90deg,var(--green),var(--blue))}.winner .name{font-weight:700;color:var(--green)}.na{color:var(--muted);font-style:italic}.legend{font-size:12px;color:var(--muted)}@media(max-width:720px){header{padding:30px 18px}h1{font-size:30px}main{padding:18px 12px}.grid{grid-template-columns:1fr}.row{grid-template-columns:110px 1fr 112px}}</style><header><div style="font-size:11px;letter-spacing:1.3px;color:#a6cdfd;font-weight:700">BLAZEPDF / BENCHMARK COMPARISON</div><h1>Which reader wins each benchmark?</h1><p id="meta"></p></header><main><div class="note">Each card is one document and one workload—the same benchmark granularity as the dashboard. A bar means that reader was measured for this exact case; shorter is faster. “Not benchmarked” means no compatible adapter is registered, not a loss or zero.</div><div class="grid" id="graphs"></div></main><script>
const D=__DATA__,R=D.measurements,$=x=>document.getElementById(x),product=r=>r.product||r.name,fm=n=>n>=1000?(n/1000).toFixed(2)+' s':n.toFixed(1)+' ms';const PRODUCTS=[...new Set(D.readers.map(product))];const missingCount=D.benchmark_cards.reduce((total,{work})=>total+PRODUCTS.filter(name=>!D.readers.some(r=>r.work===work&&product(r)===name)).length,0);$('product-count').textContent=PRODUCTS.length+' products, including BlazePDF';$('not-benchmarked-count').textContent=missingCount+' not benchmarked product/workload combinations';$('meta').textContent=D.generated_at+' · '+D.repeats+' measured runs per case · '+D.benchmark_cards.length+' benchmark cards'+(D.merged_from?' · merged from '+D.merged_from.length+' runs':'');$('graphs').innerHTML=D.benchmark_cards.map(({work,document})=>{let rows=PRODUCTS.map(name=>{let registered=D.readers.some(r=>r.work===work&&product(r)===name),value=R.find(x=>x.status==='ok'&&x.work===work&&x.document===document&&(x.product||x.reader)===name)?.median_ms;return [name,registered,value??null]});let successful=rows.filter(([,registered,time])=>registered&&time!==null).sort((a,b)=>a[2]-b[2]),max=successful.length?successful.at(-1)[2]:1,winner=successful[0]?.[0];return `<section class="card"><h2>${document}</h2><p>${work} · ${successful.length} measured reader${successful.length===1?'':'s'}</p>${rows.map(([name,registered,time])=>!registered?`<div class="row"><span class="name">${name}</span><span class="track"></span><span class="na">not benchmarked</span></div>`:time===null?`<div class="row"><span class="name">${name}</span><span class="track"></span><span class="na">no successful run</span></div>`:`<div class="row ${name===winner?'winner':''}"><span class="name">${name}</span><span class="track"><i class="fill" style="width:${Math.max(7,100*time/max)}%"></i></span><span>${fm(time)}</span></div>`).join('')}<div class="legend">${winner?`Winner: ${winner}`:'No successful run'}</div></section>`}).join('');
</script>'''.replace("__DATA__", payload)
    page = page.replace("D.repeats+' measured runs per case · '", "D.sample_count_label+' · '")
    if benchmark_note := data.get("benchmark_note"):
        visible_note = (
            '<div class="note benchmark-note"><strong>Benchmark note:</strong> '
            f'{escape(str(benchmark_note))}</div>'
        )
        page = page.replace("<main>", f"<main>{visible_note}", 1)
    machine_css = '.machine{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}.machine h2{margin:0 0 12px}.machine-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.machine-grid div{background:#f5f7fb;border-radius:8px;padding:10px}.machine-grid b,.machine-grid span{display:block}.machine-grid b{font-size:11px;color:var(--muted);text-transform:uppercase}.machine-grid span{margin-top:3px;word-break:break-word}@media(max-width:720px){.machine-grid{grid-template-columns:repeat(2,1fr)}}'
    machine_js = "const M=D.machine||{},machineFields=[['os','OS'],['cpu_model','CPU'],['cpu_count','Logical CPUs'],['memory_gb','RAM (GB)'],['gpu','GPU'],['python','Python'],['build_profile','Build']];$('machine').innerHTML=machineFields.map(([key,label])=>`<div><b>${label}</b><span>${M[key]??'unknown'}</span></div>`).join('');"
    page=page.replace('</style>',machine_css+'</style>')
    page=page.replace('</div><div class="grid" id="graphs">','</div><section class="machine"><h2>Test machine</h2><div class="machine-grid" id="machine"></div></section><div class="grid" id="graphs">',1)
    page=page.replace("$('product-count').textContent", machine_js+"$('product-count').textContent",1)
    leaderboard = '''<section class="medal-table"><h2>Medal table</h2><p>Each column is a benchmark card. A product cell shows its rank among successful measurements for that card; gold, silver and bronze indicate 1st, 2nd and 3rd. A dash means the product was not successfully measured. Ties share a rank.</p><table><thead id="medal-head"></thead><tbody id="medals"></tbody></table></section><div class="grid" id="graphs"></div>'''
    medal_script = r'''const cards=D.benchmark_cards,G=D.placement_grid,ordinal=n=>`${n}${n%100>=11&&n%100<=13?'th':({1:'st',2:'nd',3:'rd'}[n%10]||'th')}`,names=Object.keys(G),rankClass=n=>n===1?'rank-gold':n===2?'rank-silver':n===3?'rank-bronze':'',rowScore=name=>{const ranks=cards.map((_,i)=>G[name][`card_${i}`]||0).filter(Boolean);return ranks.length?ranks.reduce((a,b)=>a+b,0)/ranks.length:Infinity};$('medal-head').innerHTML=`<tr><th>Product<br><small>1st · 2nd · 3rd</small></th>${cards.map(({work,document})=>`<th title="${work}">${document}<small>${work}</small></th>`).join('')}<th title="Successful benchmark cards out of all cards">Total</th><th title="Average rank across scored cards; missing cards are ignored">Score</th></tr>`;const sorted=names.sort((a,b)=>rowScore(a)-rowScore(b)||a.localeCompare(b));$('medals').innerHTML=sorted.map(name=>{const ranks=cards.map((_,i)=>G[name][`card_${i}`]||0),scored=ranks.filter(Boolean),average=scored.length?scored.reduce((a,b)=>a+b,0)/scored.length:null,medals=[1,2,3].map(place=>ranks.filter(rank=>rank===place).length);return `<tr><th scope="row">${name}<small class="medal-summary">${medals[0]} · ${medals[1]} · ${medals[2]}</small></th>${ranks.map(rank=>`<td class="${rankClass(rank)}">${rank?ordinal(rank):'—'}</td>`).join('')}<td class="coverage-total">${scored.length} / ${cards.length}</td><td class="rank-score">${average===null?'—':average.toFixed(2)}</td></tr>`}).join('');document.querySelectorAll('#graphs .card').forEach(card=>{const score=row=>{const match=row.lastElementChild.textContent.trim().match(/^([0-9.]+)\s*(ms|s)$/);return match?Number(match[1])*(match[2]==='s'?1000:1):Infinity};const rows=[...card.querySelectorAll('.row')].sort((a,b)=>score(a)-score(b));const legend=card.querySelector('.legend');rows.forEach(row=>card.insertBefore(row,legend))});'''
    page = page.replace('</style>', '''.medal-table{margin-top:18px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:17px}.medal-table h2{font-size:16px;margin:0 0 5px}.medal-table p{margin:0 0 12px;color:var(--muted);font-size:12px}.medal-table table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:clamp(10px,.8vw,13px)}.medal-table th,.medal-table td{padding:8px 4px;text-align:center;border-top:1px solid var(--line);overflow-wrap:anywhere}.medal-table th:first-child,.medal-table td:first-child{width:132px;text-align:left}.medal-table thead th{color:var(--muted);font-size:clamp(9px,.72vw,12px)}.medal-table thead small{display:block;font-size:.78em;font-weight:400;margin-top:3px;color:var(--muted)}.medal-table tbody th{font-weight:650}.medal-summary{display:block;color:var(--muted);font-size:.78em;font-weight:500;margin-top:3px}.coverage-total,.rank-score{font-weight:700;color:var(--blue)}.rank-gold{background:#fff4c7;color:#865f00;font-weight:800}.rank-silver{background:#edf1f5;color:#526174;font-weight:800}.rank-bronze{background:#f7e6dc;color:#8a4c2d;font-weight:800}.catalog{margin-top:20px}.catalog article{padding:12px;border:1px solid var(--line);border-radius:9px;background:#fff}.catalog h3{font-size:14px;margin:0 0 4px}.catalog p{margin:3px 0;color:var(--muted);font-size:12px}.catalog-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}</style>''')
    catalog_section = '''<section class="catalog"><h2>Benchmark field & feature notes</h2><p class="legend">Catalog membership does not imply a measured score. Platform limits and performance statements are vendor descriptions, not verified results.</p><div class="catalog-grid" id="catalog"></div></section>'''
    catalog_script = r'''$('catalog').innerHTML=(D.catalog||[]).map(p=>`<article><h3><a href="${p.source}" target="_blank" rel="noreferrer">${p.name}</a> · ${p.kind}</h3><p>${p.platforms}</p><p>${p.features}</p><p><b>Claim / note:</b> ${p.claim}</p><p><b>Test candidates:</b> ${(p.tests||[]).join(' · ')||'unresolved product; no score'}</p></article>`).join('');'''
    page = page.replace('“Not benchmarked” means no compatible adapter is registered, not a loss or zero.', '“Not benchmarked” means no compatible adapter is registered, not a loss or zero. <strong id="product-count"></strong> · <strong id="not-benchmarked-count"></strong>')
    return page.replace('<div class="grid" id="graphs"></div>', leaderboard + catalog_section).replace('</script>', medal_script + catalog_script + '</script>')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.input.read_text(encoding="utf-8"))), encoding="utf-8")


if __name__ == "__main__":
    main()
