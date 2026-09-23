# 농업·화훼·원예 Daily Brief

GitHub Pages와 GitHub Actions로 운영하는 정적 일일 산업 뉴스 브리핑입니다. 평일 한국시간 오전 9시에 최신 웹 검색 결과를 바탕으로 최대 5개의 검증된 뉴스와 절화·품종 동향을 발행하고, 배포가 성공한 뒤에만 화훼업계뉴스 전용 JANDI 웹훅으로 알림을 보냅니다.

## 구조

```text
assets/                 반응형 UI, 가벼운 scroll reveal
data/YYYY-MM-DD.json    날짜별 누적 브리핑 원본
data/archive.json       아카이브용 메타데이터 (빌드 시 생성)
briefing/YYYY-MM-DD/    GitHub Pages 정적 날짜 URL (빌드 시 생성)
archive/                검색 가능한 전체 아카이브 (빌드 시 생성)
scripts/generate_briefing.py  검색·구조화 출력·중복/URL 검증
scripts/build_site.py         정적 경로와 아카이브 생성
scripts/notify_jandi.py       배포 뒤 JANDI 알림
tests/                  중복·유효성·공휴일·JANDI 단위 테스트
```

## 로컬 실행

Python 3.12 이상에서 다음을 실행합니다.

```powershell
python -m pip install -r requirements.txt
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-5.6-luna" # 선택
python scripts/generate_briefing.py
python scripts/build_site.py
python -m pytest -q
```

`.env.example`은 값의 이름만 설명하는 예시입니다. 실제 키를 `.env`에 저장했다면 그 파일은 이미 Git에서 제외됩니다. 생성기는 기존 `data/YYYY-MM-DD.json`이 있으면 덮어쓰지 않고 종료합니다. 주말과 한국 공휴일에는 생성·알림 모두 건너뜁니다.

## 최초 배포

1. 이 폴더의 내용을 새 GitHub 저장소 최상위에 push합니다.
2. **Settings → Pages → Build and deployment → Source**를 `GitHub Actions`로 선택합니다.
3. **Settings → Secrets and variables → Actions → Secrets**에 `OPENAI_API_KEY`, `JANDI_NEWS_WEBHOOK_URL`을 등록합니다. 공판장용 `JANDI_AUCTION_WEBHOOK_URL`과 섞지 않습니다.
4. 같은 화면의 **Variables**에 `SITE_URL`을 등록합니다. 예: `https://USERNAME.github.io/REPOSITORY`.
5. Actions 탭에서 **Daily briefing**을 `Run workflow`로 한 번 실행합니다.
6. 성공 후 `SITE_URL/archive/`와 `SITE_URL/briefing/YYYY-MM-DD/`를 열어 확인합니다.

필요한 값은 아래와 같습니다.

| 이름 | 위치 | 용도 |
| --- | --- | --- |
| `OPENAI_API_KEY` | GitHub Secret | OpenAI 검색 및 분석 |
| `JANDI_NEWS_WEBHOOK_URL` | GitHub Secret | 화훼업계뉴스 Incoming Webhook |
| `JANDI_AUCTION_WEBHOOK_URL` | GitHub Secret | aT 절화 경매 Incoming Webhook |
| `SITE_URL` | GitHub Variable | 배포된 날짜별 링크 생성 |
| `OPENAI_MODEL` | workflow env 또는 Variable | 선택: 사용할 모델 변경 |

## 자동화 흐름

워크플로의 `0 0 * * 1-5`는 UTC 월~금 00:00, 즉 한국시간 월~금 09:00입니다. 실행 순서는 checkout → 의존성 설치 → 한국 공휴일 검사 → 최근 30일 브리핑 비교 → OpenAI web search → JSON schema 검증/재시도 → 출처 URL 상태 확인 → 날짜 JSON 저장 → 정적 사이트 빌드 → data/route 커밋·push → Pages 배포 → JANDI 전송입니다.

출처 검증에 실패하거나 신뢰할 수 있는 항목이 부족하면 가짜 기사를 채우지 않습니다. 생성 실패는 workflow를 실패시켜 로그에서 확인할 수 있고, JANDI HTTP 상태/응답 오류도 로그에 남습니다.

## JANDI 테스트

배포 후 GitHub Actions의 수동 실행이 가장 안전한 테스트입니다. 로컬에서 실제 전송을 시험하려면 먼저 해당 날짜 JSON을 만든 다음 아래처럼 환경변수를 일시 설정합니다. 웹훅 주소는 출력하거나 커밋하지 마세요.

```powershell
$env:JANDI_NEWS_WEBHOOK_URL = "https://..."
$env:SITE_URL = "https://USERNAME.github.io/REPOSITORY"
python scripts/notify_jandi.py
```

## 운영 확인과 제한사항

Actions 실행 로그에서 `Generated ... with N verified stories`, Pages 배포 URL, `JANDI response status=200`을 확인합니다. GitHub Actions cron은 정각보다 늦게 시작될 수 있습니다. URL `HEAD` 요청을 차단하는 일부 언론사는 검증에서 빠질 수 있으며, 이미지가 없는 경우 UI의 카테고리 배경 그래픽을 사용합니다. 현재 URL 페이지 응답성과 출처 URL 생존 여부를 확인하지만, 기사 본문을 법적·편집적으로 완전 검증하는 사람의 검수까지 대체하지는 않습니다.

기사 카드 이미지는 원문이 공개한 OG/Twitter 대표 이미지를 자동으로 읽어 표시합니다. 이미지를 복제·저장하지 않고 원문 호스트의 URL을 사용하며, 제공되지 않거나 로딩이 막히면 업종별 기본 일러스트로 대체됩니다. 기존 데이터는 `python scripts/enrich_images.py --all`로 보완할 수 있습니다.
