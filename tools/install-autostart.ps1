[CmdletBinding()]
param(
    [string]$TaskName = "Telegram AI Helper"
)

$projectPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectPath ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python virtual environment was not found: $pythonPath"
}
if (-not (Test-Path -LiteralPath (Join-Path $projectPath "bot.py"))) {
    throw "bot.py was not found in: $projectPath"
}

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "bot.py" -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Starts and restarts Bahodir's Telegram AI helper after sign-in." -Force | Out-Null
Write-Output "Scheduled task '$TaskName' is installed. It will start when you next sign in to Windows."
