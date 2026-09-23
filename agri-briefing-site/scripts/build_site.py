"""Create static archive and date routes for GitHub Pages without a server."""
from __future__ import annotations
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def html_for(data_path: str, asset_prefix: str, archive_only: bool = False) -> str:
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    source = source.replace('href="assets/', f'href="{asset_prefix}assets/')
    source = source.replace('src="assets/', f'src="{asset_prefix}assets/')
    marker = f' data-briefing-path="{data_path}"'
    source = source.replace("<body>", f"<body{marker}>")
    if archive_only:
        source = source.replace('<main>', '<main data-archive-page="true">')
    return source

def main() -> None:
    archive_items = []
    for path in sorted(DATA.glob("20??-??-??.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            archive_items.append({"date": payload["date"], "title": payload.get("mostImportantChange") or "농업·화훼·원예 오늘의 핵심 동향", "signal": payload.get("signal", ""), "headlines": [s.get("shortTitle") or s.get("title") for s in payload.get("stories", [])[:3]], "categories": sorted({s.get("category", "") for s in payload.get("stories", []) if s.get("category")})})
        except (OSError, json.JSONDecodeError, KeyError) as exc: print(f"WARN skip {path}: {exc}")
    (DATA / "archive.json").write_text(json.dumps(archive_items, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = ROOT / "archive"; archive.mkdir(exist_ok=True)
    (archive / "index.html").write_text(html_for("../data/latest.json", "../", True), encoding="utf-8")
    industry = ROOT / "industry"; industry.mkdir(exist_ok=True)
    (industry / "index.html").write_text(html_for("../data/latest.json", "../"), encoding="utf-8")
    briefings = ROOT / "briefing"; briefings.mkdir(exist_ok=True)
    for item in archive_items:
        output = briefings / item["date"]; output.mkdir(parents=True, exist_ok=True)
        (output / "index.html").write_text(html_for(f"../../data/{item['date']}.json", "../../"), encoding="utf-8")
    print(f"Built {len(archive_items)} briefing routes")

if __name__ == "__main__": main()
