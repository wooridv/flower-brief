"""Generate one verified, non-duplicated Korean horticulture briefing."""
from __future__ import annotations
import json, os, time, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from openai import OpenAI
from briefing_lib import is_duplicate, is_korean_nonworking_day, validate_briefing

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KST = ZoneInfo("Asia/Seoul")
FIELDS = ["title", "shortTitle", "date", "country", "category", "sourceName", "sourceUrl", "imageUrl", "summary", "whyItMatters", "background", "technology", "marketOutlook", "businessOpportunity", "actionPoint", "keywords"]
STORY_SCHEMA = {"type": "object", "additionalProperties": False, "required": FIELDS, "properties": {field: ({"type": "array", "items": {"type": "string"}} if field == "keywords" else {"type": "string"}) for field in FIELDS}}
FLOWER_WATCH_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["flower", "variety", "signal", "evidence", "actionPoint", "sourceName", "sourceUrl"], "properties": {field: {"type": "string"} for field in ["flower", "variety", "signal", "evidence", "actionPoint", "sourceName", "sourceUrl"]}}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["date", "summary", "signal", "mostImportantChange", "attentionPoints", "flowerWatch", "actions", "stories"], "properties": {"date": {"type": "string"}, "summary": {"type": "string"}, "signal": {"type": "string"}, "mostImportantChange": {"type": "string"}, "attentionPoints": {"type": "array", "items": {"type": "string"}}, "flowerWatch": {"type": "array", "items": FLOWER_WATCH_SCHEMA}, "actions": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["title", "detail"], "properties": {"title": {"type": "string"}, "detail": {"type": "string"}}}}, "stories": {"type": "array", "items": STORY_SCHEMA}}}

def recent_stories() -> list[dict]:
    cutoff = datetime.now(KST).date() - timedelta(days=30)
    result = []
    for path in DATA.glob("20??-??-??.json"):
        if path.stem >= cutoff.isoformat():
            try: result.extend(json.loads(path.read_text(encoding="utf-8")).get("stories", []))
            except json.JSONDecodeError: print(f"WARN unreadable history: {path}")
    return result

def url_is_live(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgriBriefingBot/1.0"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=12) as response: return 200 <= response.status < 400
    except Exception as exc:
        print(f"WARN source validation failed {url}: {exc}")
        return False

def build_prompt(today: str, history: list[dict]) -> str:
    prior = [{"title": s.get("title"), "url": s.get("sourceUrl")} for s in history[-100:]]
    return f'''오늘은 {today} (Asia/Seoul)이다. web search로 오늘 또는 최근 5일의 실제 농업·화훼·원예 산업 기사를 조사해라. 국내외를 섞고 종묘·화훼·원예 기업의 사업 활용성이 높은 기사부터 최대 5개만 선택한다. 1차 출처를 우선한다.
전체 뉴스 중 적어도 2건은 화훼, 절화 소비·인기, 신품종, 육종, 품종보호, 꽃 유통 중 하나와 직접 관련된 내용을 우선 탐색한다. flowerWatch에는 현재 주목받는 절화 품목 또는 구체적인 품종명을 1~3개 넣고, 인기 신호의 근거와 실무 활용점을 작성한다. 확인된 근거가 없으면 항목 수를 줄이고 인기를 추측하지 않는다.
절대 URL, 출처, 날짜, 수치를 만들어내지 말고 검색 결과에서 확인된 사실만 쓴다. sourceUrl은 실제 원문 URL이어야 한다. imageUrl은 가능하면 원문의 OG 이미지나 공식 발표 이미지 URL을 넣고, 확인하지 못하면 빈 문자열로 둔다. 아래 최근 소개와 URL·제목·동일 사건이 중복되는 기사는 제외하라. 후속 보도만 허용하며 그 사실을 background에 밝혀라. 모든 분석은 한국어로, 사업 활용 포인트는 구체적으로 쓴다. 근거 없는 시장 수치나 예측은 금지한다.\n최근 소개: {json.dumps(prior, ensure_ascii=False)}'''

def generate(client: OpenAI, today: str, history: list[dict]) -> dict:
    last_error = "unknown error"
    for attempt in range(2):
        try:
            response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"), tools=[{"type": "web_search"}], input=build_prompt(today, history), text={"format": {"type": "json_schema", "name": "daily_briefing", "strict": True, "schema": SCHEMA}})
            payload = json.loads(response.output_text)
            payload["date"] = today
            deduplicated = []
            for story in payload.get("stories", []):
                if not is_duplicate(story, history + deduplicated): deduplicated.append(story)
            payload["stories"] = deduplicated
            errors = validate_briefing(payload, today)
            if errors: raise ValueError("; ".join(errors))
            payload["stories"] = [story for story in payload["stories"] if url_is_live(story["sourceUrl"])]
            if not payload["stories"]: raise ValueError("no source URLs passed validation")
            return payload
        except Exception as exc:
            last_error = str(exc); print(f"WARN generation attempt {attempt + 1}: {exc}"); time.sleep(2)
    raise RuntimeError(f"Briefing generation failed after retry: {last_error}")

def main() -> None:
    now = datetime.now(KST)
    if is_korean_nonworking_day(now.date()): print("Non-working day in Korea: skip"); return
    DATA.mkdir(exist_ok=True)
    today = now.date().isoformat(); destination = DATA / f"{today}.json"
    if destination.exists(): print(f"{destination} already exists; preserving it"); return
    if not os.getenv("OPENAI_API_KEY"): raise RuntimeError("OPENAI_API_KEY is required")
    payload = generate(OpenAI(), today, recent_stories())
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {destination} with {len(payload['stories'])} verified stories")

if __name__ == "__main__": main()
