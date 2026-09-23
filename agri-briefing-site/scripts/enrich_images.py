"""Backfill publisher-provided social-card image URLs in saved briefings."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from briefing_lib import enrich_story_images

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="also update archived daily JSON files")
    args = parser.parse_args()
    paths = [DATA / "latest.json"]
    if args.all:
        paths.extend(sorted(DATA.glob("20??-??-??.json")))
    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        count = enrich_story_images(payload)
        if count:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{path.name}: {count} publisher card image(s) added")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
