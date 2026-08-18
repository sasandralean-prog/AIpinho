[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 9099
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$pidFile = Join-Path $root "data\runtime\aipinho_monitor_$Port.pid"
$processId = $null

if (Test-Path -LiteralPath $pidFile) {
    $processId = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
} else {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { $processId = $listener.OwningProcess }
}

if (-not $processId) {
    Write-Output "No AIpinho monitor listener found on port $Port."
    exit 0
}

$owner = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
if (-not $owner) {
    if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force }
    Write-Output "Recorded monitor process no longer exists."
    exit 0
}
if ($owner.CommandLine -notmatch "aipinho\.apps\.monitor_main:app") {
    throw "PID $processId does not belong to AIpinho monitor; refusing to stop it."
}

Stop-Process -Id $processId -Force
if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force }
Write-Output "AIpinho monitor stopped (PID $processId)."
