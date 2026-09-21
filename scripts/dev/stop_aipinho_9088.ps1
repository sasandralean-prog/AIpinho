[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 9088
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$pidFile = Join-Path $root "data\runtime\aipinho_api_$Port.pid"
$processId = $null

if (Test-Path -LiteralPath $pidFile) {
    $recordedId = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
    $recordedOwner = Get-CimInstance Win32_Process -Filter "ProcessId = $recordedId" -ErrorAction SilentlyContinue
    $recordedListener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -eq $recordedId } |
        Select-Object -First 1
    if ($recordedOwner -and $recordedListener) {
        $processId = $recordedId
    } else {
        Remove-Item -LiteralPath $pidFile -Force
        Write-Output "Recorded PID is stale; falling back to the active listener."
    }
}

if (-not $processId) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { $processId = $listener.OwningProcess }
}

if (-not $processId) {
    Write-Output "No AIpinho listener found on port $Port."
    exit 0
}

$owner = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
if (-not $owner) {
    throw "Listener PID $processId disappeared before identity validation."
}
$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -eq $processId } |
    Select-Object -First 1
$healthIdentifiesAipinho = $false
if ($listener) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 3
        $healthIdentifiesAipinho = $health.service -eq "AIpinho"
    } catch {
        $healthIdentifiesAipinho = $false
    }
}
$commandIdentifiesAipinho = $owner.CommandLine -match "aipinho\.main:app"
if (-not $commandIdentifiesAipinho -and -not $healthIdentifiesAipinho) {
    throw "PID $processId does not belong to AIpinho; refusing to stop it."
}

Stop-Process -Id $processId -Force
$deadline = (Get-Date).AddSeconds(5)
do {
    $remainingListener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $remainingListener) { break }
    Start-Sleep -Milliseconds 100
} while ((Get-Date) -lt $deadline)

if ($remainingListener) {
    throw "AIpinho listener on port $Port remained active after stopping PID $processId."
}
if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile -Force }
Write-Output "AIpinho API stopped (PID $processId); port $Port is no longer listening."
