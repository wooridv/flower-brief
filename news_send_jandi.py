#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude(구독)가 생성한 화훼 뉴스 브리핑 텍스트를 잔디로 발송.

- 입력: 파일 경로(인자) 또는 표준입력(stdin).
- 안전장치: 빈 내용/에러 티가 나는 내용은 발송 거부, 7줄로 절단.
- 중복방지: 같은 날(KST) 이미 보냈으면 skip(--force 로 무시).

환경변수:
  JANDI_NEWS_WEBHOOK_URL  뉴스 채널 잔디 웹훅(우선). 없으면 JANDI_WEBHOOK_URL.

사용:
  python news_send_jandi.py news.txt
  cat news.txt | python news_send_jandi.py
  python news_send_jandi.py --test          # 연결 테스트
  python news_send_jandi.py news.txt --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    KST = dt.timezone(dt.timedelta(hours=9))

STATE_FILE = "news_last_sent.txt"
MAX_LINES = 7
NEWS_COLOR = "#2E7D32"  # 초록(경매 브리핑 핑크와 구분)


def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def webhook_url():
    return (os.environ.get("JANDI_NEWS_WEBHOOK_URL", "").strip()
            or os.environ.get("JANDI_WEBHOOK_URL", "").strip())


def clean_body(raw):
    """모델 출력에서 코드펜스/설명 제거 후 7줄 이내로 정리."""
    text = (raw or "").strip()
    # 혹시 감싼 코드펜스 제거
    if text.startswith("```"):
        parts = text.split("```")
        # 가운데 블록(있으면) 사용
        text = (parts[1] if len(parts) >= 2 else text).strip()
        # 첫 줄이 언어태그(예: text)면 제거
        if "\n" in text and len(text.split("\n", 1)[0]) <= 12 and " " not in text.split("\n", 1)[0]:
            text = text.split("\n", 1)[1].strip()
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[:MAX_LINES]).strip()


def looks_invalid(body):
    """발송하면 안 되는 내용인지 가벼운 휴리스틱."""
    if not body:
        return "빈 내용"
    if len(body) < 10:
        return "내용이 너무 짧음"
    low = body.lower()
    bad = ["i cannot", "i'm sorry", "죄송하지만", "error", "api error",
           "rate limit", "cannot complete"]
    if any(b in low for b in bad):
        return "에러/거부 응답으로 보임"
    return None


def post_jandi(url, body, color=NEWS_COLOR):
    data = json.dumps({"body": body, "connectColor": color}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/vnd.tosslab.jandi-v2+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")


def read_state(path=STATE_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def write_state(v, path=STATE_FILE):
    with open(path, "w", encoding="utf-8") as f:
        f.write(v)


def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(description="화훼 뉴스 브리핑 잔디 발송")
    ap.add_argument("infile", nargs="?", help="브리핑 텍스트 파일(없으면 stdin)")
    ap.add_argument("--test", action="store_true", help="연결 테스트만")
    ap.add_argument("--dry-run", action="store_true", help="발송 안 함(내용만 출력)")
    ap.add_argument("--no-state", action="store_true", help="중복방지 상태 무시")
    ap.add_argument("--force", action="store_true", help="같은 날 재발송 허용")
    args = ap.parse_args(argv)

    url = webhook_url()

    if args.test:
        if not url:
            print("JANDI_NEWS_WEBHOOK_URL(또는 JANDI_WEBHOOK_URL) 미설정", file=sys.stderr)
            return 2
        s, r = post_jandi(url, "✅ 화훼 뉴스 브리핑 웹훅 연결 테스트\n정상 수신되면 설정 완료입니다.")
        print("잔디 응답:", s, r)
        return 0 if 200 <= s < 300 else 1

    # 본문 로드
    if args.infile:
        with open(args.infile, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    body = clean_body(raw)
    bad = looks_invalid(body)
    if bad:
        print("발송 중단(%s):\n---\n%s\n---" % (bad, body[:500]), file=sys.stderr)
        return 3

    print("[발송 본문 %d줄]\n%s" % (len(body.splitlines()), body))

    if args.dry_run:
        print("\n(dry-run: 발송 안 함)")
        return 0

    today = dt.datetime.now(KST).strftime("%Y-%m-%d")
    if not args.no_state and not args.force:
        if read_state() == today:
            print("\n오늘(%s) 이미 발송함 → skip" % today)
            return 0

    if not url:
        print("JANDI_NEWS_WEBHOOK_URL(또는 JANDI_WEBHOOK_URL) 미설정 → 발송 불가", file=sys.stderr)
        return 2

    s, r = post_jandi(url, body)
    print("\n잔디 발송:", s, r)
    if 200 <= s < 300:
        write_state(today)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
