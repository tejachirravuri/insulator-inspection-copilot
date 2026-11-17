"""Download the knowledge-base PDFs listed in data/sources.toml into data/raw/.

If a manifest entry has a sha256, the downloaded file must match it; this guarantees that
everyone (and the evaluation) works on exactly the same documents.

    python scripts/fetch_documents.py
"""

import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "sources.toml"
RAW_DIR = ROOT / "data" / "raw"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    docs = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))["document"]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failed = False
    for doc in docs:
        target = RAW_DIR / f"{doc['key']}.pdf"
        if not target.exists():
            print(f"downloading {doc['key']} ...")
            request = urllib.request.Request(doc["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                target.write_bytes(response.read())
        digest = sha256_of(target)
        if doc["sha256"] and digest != doc["sha256"]:
            print(f"  MISMATCH {doc['key']}: expected {doc['sha256']}, got {digest}")
            failed = True
        else:
            print(f"  ok {doc['key']} {target.stat().st_size} bytes sha256={digest}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
