"""Pure, testable utilities for the daily briefing pipeline."""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

REQUIRED_STORY_FIELDS = {"title", "shortTitle", "date", "country", "category", "sourceName", "sourceUrl", "summary", "whyItMatters", "background", "technology", "marketOutlook", "keywords"}

class _OpenGraphParser(HTMLParser):
    """Collect the first publisher-supplied social-card image from a page."""
    def __init__(self) -> None:
        super().__init__()
        self.image: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta" or self.image:
            return
        attr = {key.lower(): (value or "").strip() for key, value in attrs}
        label = attr.get("property", attr.get("name", "")).lower()
        if label in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
            self.image = attr.get("content", "")

def is_http_url(value: str) -> bool:
    parsed = urlsplit((value or "").strip())
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc)

def publisher_image_url(source_url: str, timeout: int = 12) -> str:
    """Return an OG/Twitter image URL without downloading or copying that image."""
    if not is_http_url(source_url):
        return ""
    try:
        request = Request(source_url, headers={"User-Agent": "Mozilla/5.0 (compatible; FlowerBrief/1.0)", "Accept": "text/html,application/xhtml+xml"})
        with urlopen(request, timeout=timeout) as response:
            if response.headers.get_content_type() not in {"text/html", "application/xhtml+xml"}:
                return ""
            html = response.read(1_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            parser = _OpenGraphParser()
            parser.feed(html)
            candidate = urljoin(response.url, parser.image)
            return candidate if is_http_url(candidate) else ""
    except Exception as exc:
        print(f"WARN image metadata unavailable {source_url}: {exc}")
        return ""

def enrich_story_images(payload: dict) -> int:
    """Fill missing card image URLs from original publisher metadata."""
    added = 0
    for story in payload.get("stories", []):
        if not str(story.get("imageUrl", "")).strip():
            image = publisher_image_url(str(story.get("sourceUrl", "")))
            if image:
                story["imageUrl"] = image
                added += 1
    return added

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
    for field in ("summary", "signal", "mostImportantChange", "attentionPoints", "flowerWatch", "stories"):
        if not payload.get(field): errors.append(f"missing top-level field: {field}")
    if payload.get("date") != expected_date: errors.append("date does not match run date")
    stories = payload.get("stories", [])
    if not isinstance(stories, list) or not 1 <= len(stories) <= 5: errors.append("stories must contain 1–5 items")
    for i, story in enumerate(stories):
        missing = REQUIRED_STORY_FIELDS - set(story)
        if missing: errors.append(f"story {i + 1} missing: {', '.join(sorted(missing))}")
        if not str(story.get("sourceUrl", "")).startswith(("https://", "http://")): errors.append(f"story {i + 1} has invalid sourceUrl")
    for i, item in enumerate(payload.get("flowerWatch", [])):
        if not str(item.get("sourceUrl", "")).startswith(("https://", "http://")): errors.append(f"flowerWatch {i + 1} has invalid sourceUrl")
    return errors

def is_korean_nonworking_day(day: date) -> bool:
    import holidays
    return day.weekday() >= 5 or day in holidays.KR(years=[day.year])

def jandi_payload(briefing: dict, site_url: str) -> dict:
    items = "\n".join(f"{i}. {s.get('shortTitle') or s['title']}" for i, s in enumerate(briefing["stories"][:3], 1))
    flower_watch = briefing.get("flowerWatch", [])
    flower_line = ""
    if flower_watch:
        names = ", ".join(filter(None, [f"{x.get('flower', '')} {x.get('variety', '')}".strip() for x in flower_watch[:3]]))
        flower_line = f"\n\n🌷 절화·품종 포커스\n{names}"
    body = (f"🌱 {briefing['date']} 농업·화훼·원예 브리핑\n\n오늘의 시그널\n{briefing['signal']}\n\n주요 뉴스\n{items}{flower_line}\n\n👉 전체 브리핑 보기\n{site_url.rstrip('/')}/briefing/{briefing['date']}/")
    return {"body": body, "connectColor": "#347B55", "connectInfo": [{"title": "오늘의 핵심 동향", "description": briefing.get("summary", "")}]}
