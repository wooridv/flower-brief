from datetime import date
from scripts.briefing_lib import _OpenGraphParser, is_duplicate, is_korean_nonworking_day, jandi_payload, validate_briefing

def story(**changes):
    data = {"title":"AI 온실 제어", "shortTitle":"AI 온실", "date":"2026-09-23", "country":"KR", "category":"스마트팜", "sourceName":"공식기관", "sourceUrl":"https://example.com/news", "imageUrl":"", "summary":"요약", "whyItMatters":"의미", "background":"배경", "technology":"기술", "marketOutlook":"전망", "keywords":["AI"]}
    data.update(changes); return data

def briefing():
    flower_watch={"flower":"장미", "variety":"테스트 품종", "signal":"관심 증가", "evidence":"공식 출처 확인", "sourceName":"공식기관", "sourceUrl":"https://example.com/flower"}
    return {"date":"2026-09-23", "summary":"요약", "signal":"신호", "mostImportantChange":"변화", "attentionPoints":["포인트"], "flowerWatch":[flower_watch], "stories":[story()]}

def test_url_and_title_duplicates_are_excluded():
    history=[story(sourceUrl="https://example.com/news?utm_source=x")]
    assert is_duplicate(story(sourceUrl="https://example.com/news"), history)
    assert is_duplicate(story(title="AI-온실 제어!", sourceUrl="https://other.example/article"), history)

def test_distinct_article_is_retained():
    assert not is_duplicate(story(title="신품종 장미의 해외 출시", sourceUrl="https://example.org/rose"), [story()])

def test_valid_payload_and_invalid_url():
    assert validate_briefing(briefing(), "2026-09-23") == []
    broken=briefing(); broken["stories"][0]["sourceUrl"]="not-a-url"
    assert any("invalid sourceUrl" in x for x in validate_briefing(broken, "2026-09-23"))

def test_korean_weekend_is_nonworking_day():
    assert is_korean_nonworking_day(date(2026, 9, 26))

def test_jandi_payload_is_news_focused_and_uses_deployed_date_route():
    payload=jandi_payload(briefing(), "https://org.github.io/site/")
    assert "/briefing/2026-09-23/" in payload["body"]
    assert "JANDI_WEBHOOK_URL" not in payload["body"]
    assert "절화·품종 포커스" in payload["body"]
    assert "실행 포인트" not in payload["body"]

def test_open_graph_parser_prefers_publisher_image():
    parser = _OpenGraphParser()
    parser.feed('<meta property="og:image" content="/images/rose.jpg"><meta name="twitter:image" content="/ignored.jpg">')
    assert parser.image == "/images/rose.jpg"
