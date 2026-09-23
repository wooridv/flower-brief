<# Local Codex runner. Credentials remain on this PC: Codex ChatGPT login + .env. #>
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
    Write-Log 'Flower news run started (local Codex / ChatGPT login).'
    $gate = & python news_holiday.py 2>&1
    $gate | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "Holiday gate failed (exit=$LASTEXITCODE)." }
    if ((($gate -join "`n") -match '^SKIP:') -and -not $Force) {
        Write-Log 'Non-delivery day. Exiting without an AI call.'
        exit 0
    }

    $Codex = (Get-Command codex.cmd -ErrorAction SilentlyContinue).Source
    if (-not $Codex) { $Codex = (Get-Command codex -ErrorAction SilentlyContinue).Source }
    if (-not $Codex) {
        $candidate = Join-Path $env:APPDATA 'npm\codex.cmd'
        if (Test-Path $candidate) { $Codex = $candidate }
    }
    if (-not $Codex) { throw 'Codex CLI was not found. Install @openai/codex, then run codex login.' }
    & $Codex login status 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Codex is not logged in with ChatGPT. Run codex login interactively first.' }

    $dirty = (& git status --porcelain) | Where-Object { $_ -and $_ -notmatch '^(\?\? | M )?(jandi\.txt|raw\.json|news\.txt|logs/)' }
    if ($dirty) { throw "Uncommitted changes found. Aborting safely: $($dirty -join '; ')" }
    if (-not $NoPush) {
        & git pull --ff-only origin main 2>&1 | ForEach-Object { Write-Log $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Unable to fast-forward from origin/main.' }
    }

    $kst = [System.TimeZoneInfo]::FindSystemTimeZoneById('Korea Standard Time')
    $nowKst = [System.TimeZoneInfo]::ConvertTimeFromUtc([datetime]::UtcNow, $kst)
    $days = @('Sun','Mon','Tue','Wed','Thu','Fri','Sat')
    $prompt = "Today is {0} ({1}), Korea Standard Time.`n`n" -f $nowKst.ToString('yyyy-MM-dd'), $days[[int]$nowKst.DayOfWeek]
    $prompt += Get-Content -Raw -Encoding UTF8 (Join-Path $Root 'news_prompt.md')
    $raw = Join-Path $Root 'raw.json'
    Remove-Item -LiteralPath $raw -Force -ErrorAction SilentlyContinue
    Write-Log 'Starting Codex live web search.'
    $prompt | & $Codex exec --search --sandbox read-only --ephemeral -o $raw - 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $raw)) { throw "Codex generation failed (exit=$LASTEXITCODE)." }

    & python agri-briefing-site/scripts/import_briefing.py $raw 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "Industry briefing import failed (exit=$LASTEXITCODE)." }
    & python agri-briefing-site/scripts/build_site.py 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "Static route build failed (exit=$LASTEXITCODE)." }
    if (-not $NoPush) {
        & git add agri-briefing-site/data agri-briefing-site/archive agri-briefing-site/briefing agri-briefing-site/industry
        & git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            & git commit -m ("Horticulture industry briefing: {0}" -f $Today) 2>&1 | ForEach-Object { Write-Log $_ }
            if ($LASTEXITCODE -ne 0) { throw 'News archive commit failed.' }
            & git push origin main 2>&1 | ForEach-Object { Write-Log $_ }
            if ($LASTEXITCODE -ne 0) { throw 'Industry briefing push failed; deployment will not run.' }
        } else { Write-Log 'No archive change.' }
    }
    Write-Log 'Industry briefing generation completed. JANDI delivery waits for the 09:00 Pages deployment.'
    exit 0
}
catch {
    Write-Log ("FAILED: " + $_.Exception.Message)
    exit 1
}
