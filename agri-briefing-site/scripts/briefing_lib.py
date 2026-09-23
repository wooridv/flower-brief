"""Pure, testable utilities for the daily briefing pipeline."""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from datetime import date
from urllib.parse import urlsplit, urlunsplit

REQUIRED_STORY_FIELDS = {"title", "shortTitle", "date", "country", "category", "sourceName", "sourceUrl", "summary", "whyItMatters", "background", "technology", "marketOutlook", "businessOpportunity", "actionPoint", "keywords"}

def normalize_url(value: str) -> str:
    parsed = urlsplit((value or "").strip())
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))

def normalized_title(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (value or "").lower())

def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized_title(left), normalized_title(right)).ratio()

def is_duplicate(candidate: dict, previous: list[dict], threshold: float = .82) -> bool:
    url = normalize_url(candidate.get("sourceUrl", candidate.get("source_url", "")))
    title = candidate.get("title", "")
    for story in previous:
        old_url = normalize_url(story.get("sourceUrl", story.get("source_url", "")))
        if url and url == old_url: return True
        if title and title_similarity(title, story.get("title", "")) >= threshold: return True
    return False

def validate_briefing(payload: dict, expected_date: str) -> list[str]:
    errors: list[str] = []
    for field in ("summary", "signal", "mostImportantChange", "attentionPoints", "actions", "stories"):
        if not payload.get(field): errors.append(f"missing top-level field: {field}")
    if payload.get("date") != expected_date: errors.append("date does not match run date")
    stories = payload.get("stories", [])
    if not isinstance(stories, list) or not 1 <= len(stories) <= 5: errors.append("stories must contain 1–5 items")
    for i, story in enumerate(stories):
        missing = REQUIRED_STORY_FIELDS - set(story)
        if missing: errors.append(f"story {i + 1} missing: {', '.join(sorted(missing))}")
        if not str(story.get("sourceUrl", "")).startswith(("https://", "http://")): errors.append(f"story {i + 1} has invalid sourceUrl")
    return errors

def is_korean_nonworking_day(day: date) -> bool:
    import holidays
    return day.weekday() >= 5 or day in holidays.KR(years=[day.year])

def jandi_payload(briefing: dict, site_url: str) -> dict:
    items = "\n".join(f"{i}. {s.get('shortTitle') or s['title']}" for i, s in enumerate(briefing["stories"][:3], 1))
    action = briefing.get("actions", [{}])[0]
    body = (f"🌱 {briefing['date']} 농업·화훼·원예 브리핑\n\n오늘의 시그널\n{briefing['signal']}\n\n{items}\n\n💡 오늘의 실행 포인트\n{action.get('title', '')}\n\n👉 전체 브리핑 보기\n{site_url.rstrip('/')}/briefing/{briefing['date']}/")
    return {"body": body, "connectColor": "#347B55", "connectInfo": [{"title": "오늘의 실행 포인트", "description": action.get("detail", "")}]} 
