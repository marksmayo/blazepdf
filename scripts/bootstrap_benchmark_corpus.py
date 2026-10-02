#!/usr/bin/env python3
"""Fetch pinned corpus files, verify hashes, and never replace an existing PDF."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 64 * 1024 * 1024


def verify(content, expected):
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("fixture SHA-256 does not match its pinned manifest")
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify local fixtures without network access")
    parser.add_argument("--verify-upstream", action="store_true", help="verify downloads in memory without writing")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "benchmarks/fixture-sources.json").read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        target = (ROOT / entry["path"]).resolve()
        if not target.is_relative_to((ROOT / "vendors").resolve()):
            raise ValueError("fixture destination escapes vendors")
        url = urlparse(entry["url"])
        if url.scheme != "https" or url.netloc != "raw.githubusercontent.com":
            raise ValueError("fixture URL must use the pinned HTTPS upstream host")
        if args.check or (target.exists() and not args.verify_upstream):
            verify(target.read_bytes(), entry["sha256"])
        else:
            with urlopen(entry["url"], timeout=60) as response:
                content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError("fixture exceeds size limit")
            content = verify(content, entry["sha256"])
            if not args.verify_upstream:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(content)
        print(f"verified: {entry['path']}")


if __name__ == "__main__":
    main()
