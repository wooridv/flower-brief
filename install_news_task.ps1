<#
현재 Windows 로그인 계정으로 평일 08:00 KST 로컬 Codex 뉴스 작업을 등록한다.
작업은 '사용자가 로그온한 경우에만' 실행되므로 ChatGPT 로그인 정보가 PC 밖으로 나가지 않는다.
#>
[CmdletBinding()]
param(
    [string]$Time = '08:00',
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$TaskName = '화훼 뉴스 아침 브리핑 (로컬 Codex)'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "제거 완료: $TaskName"
    exit 0
}

$runner = Join-Path $PSScriptRoot 'run_news_brief.ps1'
if (-not (Test-Path $runner)) { throw "실행기를 찾지 못했습니다: $runner" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $runner)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "등록 완료: $TaskName / 평일 $Time / 실패 시 15분 간격 최대 3회 재시도"
Write-Host "수동 테스트: powershell -ExecutionPolicy Bypass -File `"$runner`" -Force"
