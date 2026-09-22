<#
화훼 뉴스 아침 브리핑 로컬 실행기.

AI 인증은 Codex CLI의 로컬 ChatGPT 로그인(~/.codex/auth.json)만 사용하며,
웹훅·공휴일 키는 이 폴더의 .env 에만 둔다. 어떤 인증값도 GitHub로 보내지 않는다.
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$Root = $PSScriptRoot
$LogDir = Join-Path $Root 'logs'
$Today = (Get-Date).ToString('yyyy-MM-dd')
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("news-{0}.log" -f $Today)

function Write-Log([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    $line | Tee-Object -FilePath $LogFile -Append
}

try {
    Set-Location $Root
    Write-Log '화훼 뉴스 브리핑 시작 (Codex · ChatGPT 구독 로그인)'

    # 주말·공휴일·대체공휴일에는 AI를 호출하지 않는다.
    $gate = & python news_holiday.py 2>&1
    $gate | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "공휴일 판별 실패(exit=$LASTEXITCODE)" }
    if ((($gate -join "`n") -match '^SKIP:') -and -not $Force) {
        Write-Log '발송일이 아니므로 종료'
        exit 0
    }

    # 예약 작업은 비대화형 PATH를 쓰므로 Codex 경로를 명시적으로 찾는다.
    $Codex = (Get-Command codex.cmd -ErrorAction SilentlyContinue).Source
    if (-not $Codex) { $Codex = (Get-Command codex -ErrorAction SilentlyContinue).Source }
    if (-not $Codex) {
        $candidate = Join-Path $env:APPDATA 'npm\codex.cmd'
        if (Test-Path $candidate) { $Codex = $candidate }
    }
    if (-not $Codex) {
        throw 'Codex CLI를 찾지 못했습니다. PowerShell에서 npm install -g @openai/codex 후 codex login을 실행하세요.'
    }

    & $Codex login status 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) {
        throw 'Codex가 ChatGPT 계정으로 로그인되어 있지 않습니다. PowerShell에서 codex login을 먼저 실행하세요.'
    }

    # 예약 작업이 시작되기 전 사용자가 남긴 변경을 건드리지 않도록 중단한다.
    $dirty = (& git status --porcelain) | Where-Object { $_ -and $_ -notmatch '^(\?\? | M )?(jandi\.txt|raw\.json|news\.txt|logs/)' }
    if ($dirty) { throw "커밋되지 않은 변경이 있어 안전하게 중단합니다: $($dirty -join '; ')" }

    if (-not $NoPush) {
        & git pull --ff-only origin main 2>&1 | ForEach-Object { Write-Log $_ }
        if ($LASTEXITCODE -ne 0) { throw '원격 변경을 가져오지 못했습니다. 로컬 변경을 확인하세요.' }
    }

    $kst = [System.TimeZoneInfo]::FindSystemTimeZoneById('Korea Standard Time')
    $nowKst = [System.TimeZoneInfo]::ConvertTimeFromUtc([datetime]::UtcNow, $kst)
    $prompt = "오늘은 {0} ({1}) 입니다.`n`n" -f $nowKst.ToString('yyyy년 M월 d일'), @('일','월','화','수','목','금','토')[[int]$nowKst.DayOfWeek]
    $prompt += Get-Content -Raw -Encoding UTF8 (Join-Path $Root 'news_prompt.md')
    $raw = Join-Path $Root 'raw.json'
    Remove-Item -LiteralPath $raw -Force -ErrorAction SilentlyContinue

    # --search는 Codex의 실시간 웹검색, --ephemeral은 대화 기록을 남기지 않는다.
    Write-Log 'Codex 실시간 웹검색·요약 시작'
    $prompt | & $Codex exec --search --sandbox read-only --ephemeral -o $raw - 2>&1 |
        ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $raw)) { throw "Codex 뉴스 생성 실패(exit=$LASTEXITCODE)" }

    $env:NEWS_SITE_URL = 'https://wooridv.github.io/flower-brief/news/'
    & python news_build.py $raw --data-dir news_data --jandi-out jandi.txt 2>&1 |
        ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "뉴스 데이터 생성 실패(exit=$LASTEXITCODE)" }

    # GitHub에는 공개 가능한 뉴스 JSON만 올린다. 토큰·웹훅·로그·원본은 제외된다.
    if (-not $NoPush) {
        & git add news_data
        & git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            & git commit -m ("뉴스 아카이브 업데이트: {0}" -f $Today) 2>&1 | ForEach-Object { Write-Log $_ }
            if ($LASTEXITCODE -ne 0) { throw '뉴스 아카이브 커밋 실패' }
            & git push origin main 2>&1 | ForEach-Object { Write-Log $_ }
            if ($LASTEXITCODE -ne 0) { throw '뉴스 아카이브 푸시 실패 — 사이트 링크가 최신화되지 않아 잔디 발송도 중단합니다.' }
        } else {
            Write-Log '뉴스 아카이브 변경 없음'
        }
    }

    $sendArgs = @('news_send_jandi.py', 'jandi.txt')
    if ($Force) { $sendArgs += '--force' }
    & python @sendArgs 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "잔디 발송 실패(exit=$LASTEXITCODE)" }
    Write-Log '화훼 뉴스 브리핑 완료'
    exit 0
}
catch {
    Write-Log ("실패: " + $_.Exception.Message)
    exit 1
}
