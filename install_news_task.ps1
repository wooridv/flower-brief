<# Local Windows Task Scheduler installer for the Codex flower-news runner. #>
[CmdletBinding()]
param(
    [string]$Time = '08:00',
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$TaskName = 'Flower News Brief (Local Codex)'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed: $TaskName"
    exit 0
}

$runner = Join-Path $PSScriptRoot 'run_news_brief.ps1'
if (-not (Test-Path $runner)) { throw "Runner not found: $runner" }

$actionArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $runner
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Installed: $TaskName at $Time on weekdays (3 retries, 15-minute interval)."
