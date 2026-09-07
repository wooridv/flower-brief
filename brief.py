#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aT 화훼공판장 절화(cut flower) 경매가 아침 브리핑 — 데이터 생성 + 잔디 발송.

동작:
  1) 최근 N 경매일(월/수/금, 정식 경매 = 행수 >= MIN_AUCTION_ROWS)치의 데이터를 수집.
     - f001 API: 품목/품종/등급별 정산 시세(최고/최저/평균/물량/거래액)  ← 등락 계산의 기준
     - getRealData1.json: 산지(시도)별 물량/금액                       ← 지역 지도/랭킹
  2) 각 경매일을 '직전 경매일'과 비교하여 등락·점유율을 계산, site/data/<date>.json 로 저장.
     site/data/index.json 에 날짜 목록 저장, site/index.html 에 정적 대시보드(SPA) 생성.
     → SPA 는 같은 오리진의 JSON 을 읽어 렌더(과거 날짜 탐색, 애니메이션 그래프, 산지 지도).
  3) 최신 경매일 요약(7줄 이내)을 잔디로 발송(상태 게이트로 중복/공휴일 자동 skip).

환경변수:
  FLOWER_SERVICE_KEY   flower.at.or.kr 서비스키 (필수)
  JANDI_WEBHOOK_URL    잔디 Incoming Webhook URL (발송 시 필수)
  REPORT_BASE_URL      대시보드 공개 URL (옵션, 잔디 링크에 사용)
  BACKFILL_DAYS        과거 몇 경매일치를 만들지 (기본 20)

CLI: --dry-run(발송X, 사이트는 생성) / --date YYYY-MM-DD(기준일) / --test / --no-state / --out DIR / --days N
"""

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    KST = dt.timezone(dt.timedelta(hours=9))

F001_URL = "https://flower.at.or.kr/api/returnData.api"
REAL_URL = "https://flower.at.or.kr/real/getRealData1.json"
CMP_AT_YANGJAE = "0000000001"   # aT화훼공판장(양재동)
FLOWER_GUBN_CUT = "1"           # 1:절화
MIN_AUCTION_ROWS = 200          # 정식 경매일 판별(실측: 경매일 1000행+, 비경매일 <40)
SCAN_LIMIT_DAYS = 80            # 역방향 캘린더 스캔 상한
STATE_FILE = "last_sent.txt"
REAL2_URL = "https://flower.at.or.kr/real/real2.do"

PRIORITY_ITEMS = ["백합", "튤립", "장미", "국화", "카네이션", "거베라", "수국", "리시안사스"]
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


# --------------------------------------------------------------------------
# 설정 로드
# --------------------------------------------------------------------------
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


def _num(v):
    try:
        if v in (None, ""):
            return 0.0
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _http(url, data=None, headers=None, timeout=30, retries=3):
    hdr = {"User-Agent": "flower-brief/2.0"}
    if headers:
        hdr.update(headers)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdr,
                                         method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.2 * (i + 1))
    raise RuntimeError("HTTP 실패(%s): %s" % (url, last))


# --------------------------------------------------------------------------
# 데이터 조회
# --------------------------------------------------------------------------
def fetch_f001(date_str, service_key):
    """정산 시세(품목/품종/등급). 데이터 없으면 빈 리스트."""
    q = urllib.parse.urlencode({
        "kind": "f001", "serviceKey": service_key, "baseDate": date_str,
        "flowerGubn": FLOWER_GUBN_CUT, "dataType": "json", "countPerPage": "20000",
    })
    raw = _http(F001_URL + "?" + q)
    resp = json.loads(raw).get("response", {})
    if str(resp.get("resultCd", "")) not in ("0", "00"):
        raise RuntimeError("f001 resultCd=%s (%s)" % (resp.get("resultCd"), date_str))
    items = resp.get("items") or []
    if isinstance(items, dict):
        items = [items]
    out = []
    for it in items:
        out.append({
            "pum": str(it.get("pumName", "")).strip(),
            "good": str(it.get("goodName", "")).strip(),
            "lv": str(it.get("lvNm", "")).strip(),
            "max": _num(it.get("maxAmt")), "min": _num(it.get("minAmt")),
            "avg": _num(it.get("avgAmt")), "amt": _num(it.get("totAmt")),
            "qty": _num(it.get("totQty")),
        })
    return out


def fetch_region(date_str):
    """산지(시도)별 물량/금액. 실패/무데이터 시 빈 dict."""
    yyyymmdd = date_str.replace("-", "")
    body = urllib.parse.urlencode({
        "cmpCd": CMP_AT_YANGJAE, "flowerCd": FLOWER_GUBN_CUT,
        "searchSaleDate": yyyymmdd, "itemCd": "", "itemCd2": "", "sido": "",
    }).encode("utf-8")
    try:
        raw = _http(REAL_URL, data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        rows = json.loads(raw).get("list") or []
    except Exception:  # noqa: BLE001
        return {}
    agg = {}
    for x in rows:
        s = (x.get("SANNAME") or "").strip() or "기타"
        p = (x.get("PUMNAME") or "").strip() or "(미상)"
        q = _num(x.get("QTY"))
        c = _num(x.get("COST"))
        a = agg.setdefault(s, {"qty": 0.0, "amt": 0.0, "items": {}})
        a["qty"] += q
        a["amt"] += c * q
        it = a["items"].setdefault(p, {"qty": 0.0, "amt": 0.0})
        it["qty"] += q
        it["amt"] += c * q
    return agg


# --------------------------------------------------------------------------
# 집계
# --------------------------------------------------------------------------
def aggregate_items(items):
    """품목별 물량가중 평균단가/물량/거래액."""
    agg = {}
    for it in items:
        p = it["pum"] or "(미상)"
        a = agg.setdefault(p, {"amt": 0.0, "qty": 0.0})
        a["amt"] += it["amt"]
        a["qty"] += it["qty"]
    for a in agg.values():
        a["wavg"] = (a["amt"] / a["qty"]) if a["qty"] else 0.0
    return agg


def pct(new, old):
    if not old:
        return None
    return round((new - old) / old * 100.0, 1)


def collect_auction_days(anchor, service_key, need):
    """anchor(date)부터 역방향으로 정식 경매일을 need개까지 수집.
    반환: 최신→과거 순 리스트 [(date_str, items), ...]"""
    result = []
    day = anchor
    scanned = 0
    while len(result) < need and scanned < SCAN_LIMIT_DAYS:
        ds = day.strftime("%Y-%m-%d")
        items = fetch_f001(ds, service_key)
        if len(items) >= MIN_AUCTION_ROWS:
            result.append((ds, items))
        day -= dt.timedelta(days=1)
        scanned += 1
    return result


def build_payload(date_str, items, prev_items):
    """한 경매일의 렌더용 payload(dict) 생성. prev_items 로 등락 계산."""
    agg = aggregate_items(items)
    pagg = aggregate_items(prev_items) if prev_items else {}
    total_amt = sum(a["amt"] for a in agg.values())
    total_qty = sum(a["qty"] for a in agg.values())
    prev_amt = sum(a["amt"] for a in pagg.values()) if pagg else 0.0

    item_rows = []
    for name, a in agg.items():
        prev = pagg.get(name)
        ch = pct(a["wavg"], prev["wavg"]) if prev else None
        item_rows.append({
            "name": name, "wavg": round(a["wavg"]), "qty": round(a["qty"]),
            "amt": round(a["amt"]),
            "share": round(a["amt"] / total_amt * 100, 1) if total_amt else 0,
            "change": ch,
        })
    item_rows.sort(key=lambda r: r["amt"], reverse=True)

    movers = [r for r in item_rows if r["change"] is not None and r["amt"] >= 3000000]
    risers = sorted([r for r in movers if r["change"] > 0], key=lambda r: r["change"], reverse=True)[:6]
    fallers = sorted([r for r in movers if r["change"] < 0], key=lambda r: r["change"])[:6]

    by_name = {r["name"]: r for r in item_rows}
    interest = [by_name[n] for n in PRIORITY_ITEMS if n in by_name]

    detail = sorted(
        [{"pum": it["pum"], "good": it["good"], "lv": it["lv"], "avg": round(it["avg"]),
          "max": round(it["max"]), "min": round(it["min"]), "qty": round(it["qty"]),
          "amt": round(it["amt"])} for it in items],
        key=lambda r: r["amt"], reverse=True)

    # 산지(지역)
    region_agg = fetch_region(date_str)
    reg_qty_total = sum(v["qty"] for v in region_agg.values()) or 1
    regions = []
    for k, v in region_agg.items():
        ritems = sorted(
            [{"name": ip, "qty": round(iv["qty"]), "amt": round(iv["amt"]),
              "avg": round(iv["amt"] / iv["qty"]) if iv["qty"] else 0,
              "share": round(iv["qty"] / v["qty"] * 100, 1) if v["qty"] else 0}
             for ip, iv in v["items"].items()],
            key=lambda r: r["qty"], reverse=True)[:25]  # 지역별 상위 25품목
        regions.append({"name": k, "qty": round(v["qty"]), "amt": round(v["amt"]),
                        "share": round(v["qty"] / reg_qty_total * 100, 1),
                        "items": ritems})
    regions.sort(key=lambda r: r["qty"], reverse=True)

    # 품목별 산지 최고/최저가 (지역별 물량가중 평균 낙찰단가 비교)
    item_region = {}
    for rname, rv in region_agg.items():
        for iname, iv in rv["items"].items():
            item_region.setdefault(iname, {})[rname] = iv  # {qty, amt}
    item_region_price = []
    for it in item_rows:  # 거래액 desc 순
        cand = [(rn, rv["amt"] / rv["qty"]) for rn, rv in item_region.get(it["name"], {}).items()
                if rv["qty"] >= 10]  # 소량(<10속) 지역 제외로 노이즈 방지
        if len(cand) < 2:
            continue
        cand.sort(key=lambda x: x[1])
        lo_r, lo_p = cand[0]
        hi_r, hi_p = cand[-1]
        item_region_price.append({
            "name": it["name"],
            "hi": {"region": hi_r, "price": round(hi_p)},
            "lo": {"region": lo_r, "price": round(lo_p)},
            "gapPct": round((hi_p - lo_p) / lo_p * 100, 1) if lo_p else 0,
            "regions": len(cand),
        })
        if len(item_region_price) >= 20:
            break

    d = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    return {
        "date": date_str,
        "weekday": WEEKDAY_KO[d.weekday()],
        "total": {
            "amt": round(total_amt), "qty": round(total_qty),
            "items": len(agg),
            "amtChange": pct(total_amt, prev_amt) if prev_amt else None,
        },
        "items": item_rows,
        "risers": risers, "fallers": fallers, "interest": interest,
        "regions": regions,
        "itemRegionPrice": item_region_price,
        "detail": detail,
    }


# --------------------------------------------------------------------------
# 포맷 (잔디/콘솔)
# --------------------------------------------------------------------------
def fmt_won(n):
    n = float(n)
    if n >= 1e8:
        return "%.2f억" % (n / 1e8)
    if n >= 1e4:
        return "%.1f만" % (n / 1e4)
    return "{:,}".format(int(round(n)))


def fmt_int(n):
    return "{:,}".format(int(round(float(n))))


def fmt_pct(p):
    if p is None:
        return "신규"
    a = "▲" if p > 0 else ("▼" if p < 0 else "–")
    return "%s%.1f%%" % (a, abs(p))


def sgn(p):
    if p is None:
        return "신규"
    return ("+%.1f%%" % p) if p >= 0 else ("%.1f%%" % p)


def date_label(ds):
    d = dt.datetime.strptime(ds, "%Y-%m-%d").date()
    return "%s(%s)" % (ds, WEEKDAY_KO[d.weekday()])


def jandi_body(p, prev_date, report_url=None):
    lines = []
    head = "🌸 절화 경매 브리핑 %s" % date_label(p["date"])
    if prev_date:
        head += " ※직전 %s 대비" % date_label(prev_date)
    lines.append(head)
    t = p["total"]
    tot = "총거래액 %s원" % fmt_won(t["amt"])
    if t["amtChange"] is not None:
        tot += "(%s)" % fmt_pct(t["amtChange"])
    tot += " · 물량 %s속 · %d품목" % (fmt_won(t["qty"]), t["items"])
    lines.append(tot)
    if p["risers"]:
        lines.append("📈 " + " · ".join("%s %s" % (r["name"], sgn(r["change"])) for r in p["risers"][:3]))
    if p["fallers"]:
        lines.append("📉 " + " · ".join("%s %s" % (r["name"], sgn(r["change"])) for r in p["fallers"][:3]))
    if p["interest"]:
        seg = []
        for r in p["interest"][:3]:
            s = "%s %s원" % (r["name"], fmt_int(r["wavg"]))
            if r["change"] is not None:
                s += "(%s)" % sgn(r["change"])
            seg.append(s)
        lines.append("· " + " · ".join(seg))
    if p["regions"]:
        lines.append("🌏 산지 " + " · ".join("%s %.0f%%" % (r["name"], r["share"]) for r in p["regions"][:3]))
    if report_url:
        lines.append("🔗 상세: %s" % report_url)
    return "\n".join(lines[:7])


def console_summary(p, prev_date):
    out = ["=" * 56,
           "절화 경매 브리핑  %s   직전 %s" % (date_label(p["date"]),
                                          date_label(prev_date) if prev_date else "-"),
           "=" * 56]
    t = p["total"]
    out.append("총거래액 %s원 (전대비 %s) · 물량 %s속 · 품목 %d종"
               % (fmt_won(t["amt"]), fmt_pct(t["amtChange"]) if t["amtChange"] is not None else "-",
                  fmt_int(t["qty"]), t["items"]))
    out.append("상승: " + ", ".join("%s %s" % (r["name"], sgn(r["change"])) for r in p["risers"][:5]))
    out.append("하락: " + ", ".join("%s %s" % (r["name"], sgn(r["change"])) for r in p["fallers"][:5]))
    if p["regions"]:
        out.append("산지: " + ", ".join("%s %s속(%.0f%%)" % (r["name"], fmt_int(r["qty"]), r["share"])
                                       for r in p["regions"][:5]))
    return "\n".join(out)


# --------------------------------------------------------------------------
# 사이트 출력
# --------------------------------------------------------------------------
def write_site(payloads, out_dir):
    """payloads: 최신→과거 순 dict 리스트. data/*.json, data/index.json, index.html 생성."""
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    for p in payloads:
        with open(os.path.join(data_dir, p["date"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, separators=(",", ":"))
    index = {
        "generated": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "latest": payloads[0]["date"] if payloads else None,
        "dates": [{"date": p["date"], "weekday": p["weekday"],
                   "amt": p["total"]["amt"], "amtChange": p["total"]["amtChange"]}
                  for p in payloads],
    }
    with open(os.path.join(data_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(SPA_HTML)
    # 산지 지도용 경량 GeoJSON 번들 복사(스크립트와 같은 폴더)
    geo_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "korea_provinces.geojson")
    if os.path.exists(geo_src):
        shutil.copyfile(geo_src, os.path.join(out_dir, "korea_provinces.geojson"))


# --------------------------------------------------------------------------
# 잔디 / 상태
# --------------------------------------------------------------------------
def post_jandi(url, body, color="#E7568C"):
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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(description="화훼 절화 경매 아침 브리핑")
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--no-state", action="store_true")
    ap.add_argument("--out", default="site")
    ap.add_argument("--days", type=int, default=int(os.environ.get("BACKFILL_DAYS", "20")))
    args = ap.parse_args(argv)

    webhook = os.environ.get("JANDI_WEBHOOK_URL", "").strip()
    if args.test:
        if not webhook:
            print("JANDI_WEBHOOK_URL 미설정", file=sys.stderr)
            return 2
        s, r = post_jandi(webhook, "✅ 화훼 브리핑 웹훅 연결 테스트\n정상 수신되면 설정 완료입니다.")
        print("잔디 응답:", s, r)
        return 0

    key = os.environ.get("FLOWER_SERVICE_KEY", "").strip()
    if not key:
        print("FLOWER_SERVICE_KEY 미설정", file=sys.stderr)
        return 2
    report_url = os.environ.get("REPORT_BASE_URL", "").strip() or None

    anchor = (dt.datetime.strptime(args.date, "%Y-%m-%d").date()
              if args.date else dt.datetime.now(KST).date())

    # 최신 포함 need+1 경매일 수집(가장 오래된 날의 등락 비교용 1개 추가)
    need = max(1, args.days) + 1
    print("경매일 수집 중(최대 %d개)..." % need)
    days = collect_auction_days(anchor, key, need)
    if not days:
        print("최근 경매 데이터 없음 → 종료")
        return 0

    # payload 생성(각 날짜는 바로 다음(과거) 경매일과 비교)
    payloads = []
    for i in range(len(days)):
        ds, items = days[i]
        prev_items = days[i + 1][1] if i + 1 < len(days) else None
        print("  build %s (rows=%d)" % (ds, len(items)))
        payloads.append(build_payload(ds, items, prev_items))
    payloads = payloads[:args.days]  # 표시용 N개

    write_site(payloads, args.out)
    latest = payloads[0]
    prev_date = payloads[1]["date"] if len(payloads) > 1 else None

    print("\n" + console_summary(latest, prev_date))
    print("\n[사이트] %s  (%d 경매일)" % (os.path.join(args.out, "index.html"), len(payloads)))

    body = jandi_body(latest, prev_date, report_url)
    print("\n[잔디 %d줄]\n%s" % (len(body.splitlines()), body))

    if args.dry_run:
        print("\n(dry-run: 발송 안 함)")
        return 0

    if not args.no_state:
        last = read_state()
        if last and latest["date"] <= last:
            print("\n이미 브리핑함(last=%s) → skip" % last)
            return 0
    if not webhook:
        print("JANDI_WEBHOOK_URL 미설정 → 발송 불가", file=sys.stderr)
        return 2
    s, r = post_jandi(webhook, body)
    print("\n잔디 발송:", s, r)
    if 200 <= s < 300:
        write_state(latest["date"])
        return 0
    return 1


# SPA_HTML 는 파일 하단에 정의
from app_html import SPA_HTML  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
