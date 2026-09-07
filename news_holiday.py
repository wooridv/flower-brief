#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오늘(KST) 이 '브리핑 발송일'인지(=평일 & 비공휴일) 판별.

우선순위:
  1) HOLIDAY_SERVICE_KEY(data.go.kr 특일정보 서비스키)가 있으면 API로 공휴일 조회
     — 대체공휴일 포함, 매년 자동 최신화. (권장)
  2) 키가 없거나 조회 실패 시, 아래 번들 공휴일표(2026~2027)로 판별.
     — 표에 없는 연도는 '주말만 제외'로 동작(fail-open: 막지 않고 발송).

사용:
  python news_holiday.py                # 사람이 읽는 결과 출력
  python news_holiday.py --github       # GITHUB_OUTPUT 에 skip/reason 기록(워크플로 게이트용)
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    KST = dt.timezone(dt.timedelta(hours=9))

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

# 번들 공휴일표(대체공휴일 포함). YYYY-MM-DD → 명칭.
# ※ 음력/대체공휴일은 매년 바뀌므로, HOLIDAY_SERVICE_KEY 사용을 권장.
#   미사용 시 연 1회 갱신하거나 새해 전 연도 추가.
BUNDLED_HOLIDAYS = {
    # 2026
    "2026-01-01": "신정",
    "2026-02-16": "설날 연휴", "2026-02-17": "설날", "2026-02-18": "설날 연휴",
    "2026-03-01": "삼일절", "2026-03-02": "삼일절 대체공휴일",
    "2026-05-05": "어린이날",
    "2026-05-24": "부처님오신날", "2026-05-25": "부처님오신날 대체공휴일",
    "2026-06-06": "현충일",
    "2026-08-15": "광복절", "2026-08-17": "광복절 대체공휴일",
    "2026-09-24": "추석 연휴", "2026-09-25": "추석", "2026-09-26": "추석 연휴",
    "2026-09-28": "추석 대체공휴일",
    "2026-10-03": "개천절", "2026-10-05": "개천절 대체공휴일",
    "2026-10-09": "한글날",
    "2026-12-25": "성탄절",
    # 2027 (음력 명절은 발표 기준 예상 — HOLIDAY_SERVICE_KEY 사용 시 자동 정정)
    "2027-01-01": "신정",
    "2027-02-06": "설날 연휴", "2027-02-07": "설날", "2027-02-08": "설날 연휴",
    "2027-02-09": "설날 대체공휴일",
    "2027-03-01": "삼일절",
    "2027-05-05": "어린이날",
    "2027-05-13": "부처님오신날",
    "2027-06-06": "현충일", "2027-06-07": "현충일 대체공휴일",
    "2027-08-15": "광복절", "2027-08-16": "광복절 대체공휴일",
    "2027-09-14": "추석 연휴", "2027-09-15": "추석", "2027-09-16": "추석 연휴",
    "2027-10-03": "개천절", "2027-10-04": "개천절 대체공휴일",
    "2027-10-09": "한글날", "2027-10-11": "한글날 대체공휴일",
    "2027-12-25": "성탄절",
}


def _holiday_name_via_api(d, key):
    """data.go.kr 특일정보 API로 해당 월 공휴일 조회 → {YYYY-MM-DD: 명칭}. 실패 시 None."""
    url = ("http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/"
           "getRestDeInfo")
    q = urllib.parse.urlencode({
        "serviceKey": key, "solYear": "%04d" % d.year, "solMonth": "%02d" % d.month,
        "_type": "json", "numOfRows": "100",
    })
    req = urllib.request.Request(url + "?" + q,
                                 headers={"User-Agent": "flower-news/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    items = (((data.get("response") or {}).get("body") or {}).get("items") or {})
    items = items.get("item") if isinstance(items, dict) else items
    if items is None:
        return {}
    if isinstance(items, dict):
        items = [items]
    out = {}
    for it in items:
        if str(it.get("isHoliday", "")).strip().upper() != "Y":
            continue
        loc = str(it.get("locdate", "")).strip()  # YYYYMMDD
        if len(loc) == 8:
            iso = "%s-%s-%s" % (loc[:4], loc[4:6], loc[6:8])
            out[iso] = str(it.get("dateName", "공휴일")).strip()
    return out


def holiday_name(d):
    """d(date)가 공휴일이면 명칭, 아니면 None. (주말은 별도 처리)"""
    key = os.environ.get("HOLIDAY_SERVICE_KEY", "").strip()
    iso = d.strftime("%Y-%m-%d")
    if key:
        try:
            return _holiday_name_via_api(d, key).get(iso)
        except Exception as e:  # noqa: BLE001 - API 실패 시 번들표로 폴백
            print("  ! 공휴일 API 실패, 번들표로 폴백: %s" % e, file=sys.stderr)
    return BUNDLED_HOLIDAYS.get(iso)


def should_skip(today=None):
    """(skip: bool, reason: str). 주말/공휴일이면 skip=True."""
    d = today or dt.datetime.now(KST).date()
    label = "%s(%s)" % (d.strftime("%Y-%m-%d"), WEEKDAY_KO[d.weekday()])
    if d.weekday() >= 5:  # 5=토, 6=일
        return True, "주말 %s" % label
    name = holiday_name(d)
    if name:
        return True, "공휴일 %s · %s" % (label, name)
    return False, "평일 %s" % label


def main(argv=None):
    ap = argparse.ArgumentParser(description="브리핑 발송일 판별")
    ap.add_argument("--github", action="store_true",
                    help="$GITHUB_OUTPUT 에 skip/reason 기록")
    ap.add_argument("--date", help="YYYY-MM-DD (테스트용, 기본 오늘 KST)")
    args = ap.parse_args(argv)

    today = (dt.datetime.strptime(args.date, "%Y-%m-%d").date()
             if args.date else None)
    skip, reason = should_skip(today)

    print(("SKIP: " if skip else "GO: ") + reason)

    gh = os.environ.get("GITHUB_OUTPUT")
    if args.github and gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write("skip=%s\n" % ("true" if skip else "false"))
            f.write("reason=%s\n" % reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
