import json
from pathlib import Path

data = json.loads((Path(__file__).resolve().parents[1] / "results" / ".canonical-input.json").read_text(encoding="utf-8"))
products = {r.get("product", r["name"]) for r in data["readers"]} | {p["name"] for p in data.get("catalog", [])}
cards = {(m["work"], m["document"]) for m in data["measurements"]}
pair_by_work = {}
for reader in data["readers"]:
    pair_by_work.setdefault(reader["work"], set()).add(reader.get("product", reader["name"]))
missing = sum(len(products) - len(pair_by_work.get(work, set())) for work, _ in cards)
print(f"measurements={len(data['measurements'])} products={len(products)} cards={len(cards)} missing={missing}")
