#!/usr/bin/env python3
"""Register a repository and scaffold its benchmark adapter."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "benchmarks" / "readers.json"

if len(sys.argv) != 2 or not re.match(r"https://github\.com/[^/]+/[^/#]+/?$", sys.argv[1]):
    raise SystemExit("Usage: python scripts/add_reader.py https://github.com/owner/repository")

url = sys.argv[1].rstrip("/")
slug = url.rsplit("/", 1)[-1].lower()
target = ROOT / "vendors" / slug
data = json.loads(CONFIG.read_text(encoding="utf-8"))
if any(item["repository"].rstrip("/") == url for item in data["readers"]):
    raise SystemExit(f"Already registered: {url}")
if not target.exists():
    subprocess.run(["git", "clone", "--depth", "1", url, str(target)], check=True)
data["readers"].append({
    "id": slug, "name": slug, "repository": url, "path": f"vendors/{slug}",
    "adapter": "external-binary", "work": "not configured", "command": None
})
CONFIG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Registered {slug}. Configure its command in benchmarks/readers.json.")
