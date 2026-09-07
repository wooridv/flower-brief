#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude(구독) 웹검색 출력(JSON)을 받아 → 사이트 아카이브 + 잔디 발송본 생성.

입력: Claude 가 뽑은 원본(JSON, 코드펜스/잡텍스트 섞여 있어도 됨) — 파일 또는 stdin.
동작:
  1) 첫 JSON 객체를 견고하게 추출·검증.
  2) 오늘(KST) 날짜/요일 부여 → news_data/<date>.json 저장.
  3) news_data/index.json 갱신(최신순, 중복 제거).
  4) 잔디 발송본(7줄 이내) 텍스트를 out(기본 jandi.txt)로 저장.

사용:
  python news_build.py raw.json                 # 파일 입력
  claude ... | python news_build.py             # stdin 입력
  python news_build.py raw.json --jandi-out jandi.txt --data-dir news_data
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    KST = dt.timezone(dt.timedelta(hours=9))

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
MAX_JANDI_LINES = 7
TAG_RE = re.compile(r"<[^>]+>")


def extract_json(raw):
    """문자열에서 첫 번째 완결 JSON 객체를 추출."""
    text = (raw or "").strip()
    # 코드펜스 제거
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
        if m:
            text = m.group(1).strip()
    # 첫 '{' 부터 균형 맞는 '}' 까지
    start = text.find("{")
    if start < 0:
        raise ValueError("JSON 객체를 찾지 못함")
    depth, instr, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("JSON 객체가 닫히지 않음")


def strip_tags(s):
    return TAG_RE.sub("", s or "").strip()


def short_url(u):
    return re.sub(r"^https?://(www\.)?", "", u or "").rstrip("/")


def validate(obj):
    if not isinstance(obj, dict):
        raise ValueError("최상위가 객체가 아님")
    items = obj.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("items 가 비었음")
    clean = []
    for it in items:
        if not isinstance(it, dict):
            continue
        head = strip_tags(it.get("head"))
        if not head:
            continue
        clean.append(it)
    if len(clean) < 2:
        raise ValueError("유효한 items 가 너무 적음(%d)" % len(clean))
    obj["items"] = items  # 원본(스팬 포함) 유지 — 사이트에서 사용
    obj.setdefault("keywords", [])
    obj.setdefault("lead", "")
    return obj


def build_jandi(obj, date, weekday):
    d = dt.datetime.strptime(date, "%Y-%m-%d").date()
    lines = ["🌷 화훼시장 아침 브리핑 %d/%d(%s)" % (d.month, d.day, weekday)]
    for it in obj["items"]:
        if len(lines) >= MAX_JANDI_LINES:
            break
        icon = (it.get("icon") or "•").strip()
        head = strip_tags(it.get("head"))
        line = "%s %s" % (icon, head)
        if it.get("url"):
            line += " (%s)" % short_url(it["url"])
        lines.append(line)
    return "\n".join(lines[:MAX_JANDI_LINES])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Claude JSON → 사이트 아카이브 + 잔디 발송본")
    ap.add_argument("infile", nargs="?", help="원본 JSON 파일(없으면 stdin)")
    ap.add_argument("--data-dir", default="news_data")
    ap.add_argument("--jandi-out", default="jandi.txt")
    ap.add_argument("--date", help="YYYY-MM-DD (기본 오늘 KST)")
    args = ap.parse_args(argv)

    raw = open(args.infile, "r", encoding="utf-8").read() if args.infile else sys.stdin.read()
    try:
        obj = validate(extract_json(raw))
    except Exception as e:  # noqa: BLE001
        print("생성 결과 파싱 실패: %s\n---\n%s" % (e, raw[:800]), file=sys.stderr)
        return 3

    today = (dt.datetime.strptime(args.date, "%Y-%m-%d").date()
             if args.date else dt.datetime.now(KST).date())
    date = today.strftime("%Y-%m-%d")
    weekday = WEEKDAY_KO[today.weekday()]
    obj["date"] = date
    obj["weekday"] = weekday

    os.makedirs(args.data_dir, exist_ok=True)
    with open(os.path.join(args.data_dir, date + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

    # index 갱신(최신순, 중복 제거)
    idx_path = os.path.join(args.data_dir, "index.json")
    try:
        idx = json.load(open(idx_path, "r", encoding="utf-8"))
        dates = [d for d in idx.get("dates", []) if d.get("date") != date]
    except Exception:  # noqa: BLE001
        dates = []
    dates.append({"date": date, "weekday": weekday, "lead": obj.get("lead", "")})
    dates.sort(key=lambda d: d["date"], reverse=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump({"generated": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                   "latest": dates[0]["date"], "dates": dates},
                  f, ensure_ascii=False, indent=1)

    jandi = build_jandi(obj, date, weekday)
    with open(args.jandi_out, "w", encoding="utf-8") as f:
        f.write(jandi)

    print("✔ 아카이브 저장: %s/%s.json  (총 %d일)" % (args.data_dir, date, len(dates)))
    print("✔ 잔디 발송본(%d줄): %s\n---\n%s" % (len(jandi.splitlines()), args.jandi_out, jandi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
