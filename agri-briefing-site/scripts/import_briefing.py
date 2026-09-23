"""Validate Codex web-search JSON and save it into the static briefing archive."""
from __future__ import annotations
import argparse, json, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from briefing_lib import is_duplicate, validate_briefing

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KST = ZoneInfo("Asia/Seoul")

def extract_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced: text = fenced.group(1)
    start = text.find("{")
    if start < 0: raise ValueError("JSON object not found")
    depth = 0; quoted = False; escaped = False
    for index, char in enumerate(text[start:], start):
        if quoted:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char == "{": depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0: return json.loads(text[start:index + 1])
    raise ValueError("JSON object is incomplete")

def previous_stories(today: str) -> list[dict]:
    result = []
    for path in DATA.glob("20??-??-??.json"):
        if path.stem != today:
            try: result.extend(json.loads(path.read_text(encoding="utf-8")).get("stories", []))
            except (OSError, json.JSONDecodeError): pass
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    today = datetime.now(KST).date().isoformat()
    destination = DATA / f"{today}.json"
    if destination.exists(): print(f"{destination} already exists; preserving it"); return 0
    payload = extract_json(Path(args.input).read_text(encoding="utf-8"))
    payload["date"] = today
    history = previous_stories(today); unique = []
    for story in payload.get("stories", []):
        if not is_duplicate(story, history + unique): unique.append(story)
    payload["stories"] = unique
    errors = validate_briefing(payload, today)
    if errors: raise ValueError("; ".join(errors))
    DATA.mkdir(exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    destination.write_text(rendered, encoding="utf-8")
    (DATA / "latest.json").write_text(rendered, encoding="utf-8")
    print(f"Imported {len(unique)} verified stories into {destination}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
