# 🌸 화훼 절화 경매 브리핑

aT 화훼공판장(양재동)의 **절화 경매 정산가**를 매 평일 아침 09:00(KST)에
**잔디(JANDI)** 로 요약 발송하고, 전체 상세는 **웹 대시보드(GitHub Pages)** 로 제공합니다.

## 구성

- **잔디 요약(7줄 이내)**: 총거래액·물량·품목수, 직전 경매 대비 상승/하락 TOP, 주요 품목 단가, 산지 TOP3, 상세 링크
- **웹 대시보드**(모바일·PC 대응, 다크모드):
  - 총괄(거래액 카운트업 + 전 경매 대비 등락 배지)
  - **많이 나간 품목 TOP 10** — 거래액 점유율 애니메이션 막대
  - **산지별 반입 지도** — 한국 시도 choropleth(색 진할수록 반입량↑) + 지역 랭킹
  - 가격 상승/하락 TOP, 품목 요약표, 품종·등급별 전체 표(검색)
  - **과거 경매일 탐색** — 상단 날짜 선택 + ◀▶ 로 지난 경매일 다시 보기(기본 최근 20경매일)

## 데이터 출처

- **f001 API**(`flower.at.or.kr/api/returnData.api`) — 품목/품종/등급별 정산 시세(등락 기준)
- **실시간 경매 API**(`flower.at.or.kr/real/getRealData1.json`) — 산지(시도)별 물량(지도/랭킹)
- 지도 경계: `korea_provinces.geojson`(레포에 번들된 경량 17개 시도 GeoJSON, 33KB)
- 원본 실시간 상세: [flower.at.or.kr/real/real2.do](https://flower.at.or.kr/real/real2.do)

## 동작 방식

- 절화 정식 경매일은 **월·수·금**(행수 1,000+), 비경매일은 소량 잔여 거래뿐 → 자동 구분(임계값 200행).
- 경매일 데이터는 **당일 아침엔 없고 그날 중 공개**되므로, 각 경매는 **다음 평일 아침**에 브리핑됩니다.
  (금 경매→월 아침, 월 경매→화 아침)
- `last_sent` 상태값으로 **같은 경매 중복 발송 방지**. 공휴일·임시공휴일은 데이터가 없어 자동 skip.

## 설정 (GitHub Actions)

1. 이 폴더를 **GitHub public 레포**로 push (Pages 무료 사용 · 꽃 경매가는 공개 데이터).
2. **Settings → Secrets and variables → Actions** 에 등록:
   - `FLOWER_SERVICE_KEY` = 발급받은 flower.at.or.kr 서비스키
   - `JANDI_WEBHOOK_URL` = 잔디 Incoming Webhook URL
3. **Settings → Pages → Source = "GitHub Actions"**.
4. 끝. 매 평일 09:00 KST 자동 실행. 즉시 확인은 **Actions 탭 → Run workflow**.

대시보드 주소: `https://<GitHub계정>.github.io/<레포이름>/`

## 로컬 테스트 (외부 라이브러리 불필요, 파이썬 3.9+)

```bash
# .env.example → .env 복사 후 값 채우기

python brief.py --dry-run --date 2026-09-04    # 특정 경매일 미리보기 + site/ 생성(발송 X)
python brief.py --dry-run                       # 오늘 기준 자동(최신 경매일)
python brief.py --test                          # 잔디 웹훅 연결 테스트
python brief.py --no-state                      # 상태 무시하고 실제 발송

# 대시보드 로컬 확인(정적 파일이라 서버 필요):
python -m http.server 8777 --directory site     # → http://localhost:8777
```

옵션: `--days N`(과거 몇 경매일치 생성, 기본 20) 또는 환경변수 `BACKFILL_DAYS`.

## 파일

| 파일 | 설명 |
|---|---|
| `brief.py` | 데이터 수집·집계·등락/점유율 계산·사이트 생성·잔디 발송·상태관리 |
| `app_html.py` | 웹 대시보드(SPA) HTML/CSS/JS |
| `korea_provinces.geojson` | 산지 지도용 경량 한국 시도 경계(번들) |
| `.github/workflows/flower-brief.yml` | 매 평일 09:00 KST 실행 + Pages 배포 |
| `.env.example` · `.gitignore` | 로컬 환경변수 예시 · 제외 목록 |

## 참고

- 단가는 **원/속**, 수수료 미포함, 양재동 화훼공판장 전자경매 정산가 기준.
- 튤립·카네이션 등 일부 품목은 **계절에 따라 없는 날**이 있어, 주요 품목 표기는 그날 존재하는 품목에서 자동 선택.
- 산지 물량은 실시간 경매 API 기준(정정·하자처리 미반영 참고용), 시세는 f001 정산가 기준.

---

# 🌷 화훼 뉴스 아침 브리핑 (별도 시스템)

경매 정산가(숫자) 브리핑과 **별개**로, 매 평일 아침 **화훼·절화 시장 뉴스/유행/분위기**를
로컬 PC의 **Codex CLI(ChatGPT 구독 로그인)** 가 실시간 웹검색해 **잔디**(7줄 요약)와
**웹 뉴스 사이트**로 전합니다. AI 인증·잔디 웹훅은 GitHub에 저장하지 않습니다.

## 동작 방식

1. **발송일 판별**(`news_holiday.py`): 주말·공휴일·대체공휴일이면 자동 skip.
   - `HOLIDAY_SERVICE_KEY`(data.go.kr 특일정보) 있으면 자동 최신화, 없으면 번들 공휴일표(2026~2027).
2. **뉴스 생성**: Windows 작업 스케줄러가 `run_news_brief.ps1`을 실행 → **Codex CLI의 로컬
   ChatGPT 로그인**으로 실시간 웹검색 → `news_prompt.md` 규격의 **JSON** 생성(API 키·종량제 없음).
3. **취합**(`news_build.py`): JSON을 검증해 오늘 날짜로 `news_data/<date>.json` 저장 +
   `news_data/index.json`(최신순 목록) 갱신 → **공개 가능한 뉴스 결과만 레포에 커밋**. 동시에 잔디 발송본(7줄) 생성.
4. **발송**(`news_send_jandi.py`): 잔디 발송본을 검증·발송(같은 날 중복방지). 경매(핑크)와 구분해 **초록색**.
5. **웹 사이트**(`news_site.html`): 최신+과거 브리핑을 보여주는 SPA. 경매 대시보드 Pages에 **함께 배포**(`/news/`).
   - 고딕 디자인 · 꽃잎 모션 · ◀▶/🗓️ 지난 브리핑 아카이브 · 뉴스별 출처 링크.
   - 뉴스 페이지는 경매 워크플로가 `news_data`+`news_site.html`을 `site/news/`로 복사해 배포하므로,
     **웹 갱신은 경매 배포 시각(09:00)**, 잔디는 08:00.

- 실행 시각: 매 평일 **08:00 KST**(잔디). 실패 시 15분 간격으로 최대 3회 재시도.
- 뉴스 사이트 주소: `https://<계정>.github.io/<레포>/news/`

## 설정 (로컬 Codex + Windows 작업 스케줄러)

1. Codex CLI 설치·ChatGPT 로그인(최초 1회):
   ```powershell
   npm install -g @openai/codex
   codex login
   ```
2. `.env.example`을 `.env`로 복사하고 **로컬에만** `JANDI_NEWS_WEBHOOK_URL`을 입력합니다.
   `.env`는 `.gitignore`로 제외되어 절대 커밋되지 않습니다.
3. 작업 등록(최초 1회):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install_news_task.ps1
   ```
   - 현재 로그인한 Windows 계정에서만 실행되므로 Codex 로그인 정보가 PC 밖으로 나가지 않습니다.
   - PC가 꺼져 있었으면 켜진 뒤 가능한 때 실행합니다.
4. 수동 전체 테스트:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_news_brief.ps1 -Force
   ```
   로그는 `logs/news-YYYY-MM-DD.log`에만 남습니다.

### GitHub에서 제거할 이전 비밀값

이전 Claude 자동화는 `.github/workflows/flower-news.yml.disabled`로 비활성화했습니다.
GitHub의 **Settings → Secrets and variables → Actions**에서 아래 기존 Secret도 직접 삭제하세요.

- `CLAUDE_CODE_OAUTH_TOKEN`
- `JANDI_NEWS_WEBHOOK_URL`
- 뉴스 자동화만을 위해 만들었던 `HOLIDAY_SERVICE_KEY` (경매 브리핑에도 쓰면 유지)

## 로컬 테스트

```bash
python news_holiday.py --date 2026-09-28     # 발송일 판별(SKIP/GO)
python news_build.py raw.json --data-dir news_data --jandi-out jandi.txt  # JSON→아카이브+발송본
python news_send_jandi.py jandi.txt --dry-run    # 발송 본문 미리보기(발송 X)
python news_send_jandi.py --test             # 잔디 웹훅 연결 테스트

# 사이트 로컬 확인(정적):
python -m http.server 8778   # → http://localhost:8778/news_site.html (시드 데이터로 렌더)
```

## 뉴스 브리핑 파일

| 파일 | 설명 |
|---|---|
| `run_news_brief.ps1` | 로컬 Codex 실행·공휴일 판별·아카이브 푸시·잔디 발송(핵심) |
| `install_news_task.ps1` | 평일 08:00 Windows 작업 스케줄러 등록/해제 |
| `news_prompt.md` | Codex 브리핑 작성 지침(실시간 웹검색 → JSON 규격) |
| `news_build.py` | Codex JSON 검증 → `news_data/` 아카이브 갱신 + 잔디 발송본 생성 |
| `news_holiday.py` | 주말/공휴일/대체공휴일 판별(API 우선, 번들표 폴백) |
| `news_send_jandi.py` | 잔디 발송본 검증·발송·중복방지 |
| `news_site.html` | 뉴스 사이트 SPA(최신+아카이브, 모션, 링크) — Pages `/news/` |
| `news_data/*.json` | 일자별 브리핑 아카이브 + `index.json`(목록) — 로컬 Codex가 커밋 |
| `.github/workflows/flower-news.yml.disabled` | 이전 Claude/GitHub Actions 워크플로(비활성화 기록) |

> 참고: 웹훅·공휴일 키는 로컬 `.env`, Codex 인증은 로컬 로그인 저장소에만 있습니다.
> `raw.json`·`jandi.txt`·`logs/`는 실행 산출물이라 `.gitignore` 처리(아카이브는 `news_data/`에만 커밋).
