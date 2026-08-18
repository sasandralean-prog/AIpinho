[CmdletBinding()]
param(
    [string]$HostName = "0.0.0.0",
    [ValidateRange(1, 65535)]
    [int]$Port = 9080,
    [string]$PythonPath = "",
    [int]$StartupTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path

if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
    if ($owner -and $owner.CommandLine -match "aipinho\.apps\.bootstrap_control_main:app") {
        Write-Output "AIpinho bootstrap control already listening on port $Port (PID $($listener.OwningProcess))."
        exit 0
    }
    throw "Port $Port is already used by PID $($listener.OwningProcess); refusing to replace an unrelated process."
}

$runtimeDir = Join-Path $root "data\runtime"
$logDir = Join-Path $root "data\logs\runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir,$logDir | Out-Null
$pidFile = Join-Path $runtimeDir "aipinho_bootstrap_$Port.pid"
$stdout = Join-Path $logDir "aipinho_bootstrap_$Port.out.log"
$stderr = Join-Path $logDir "aipinho_bootstrap_$Port.err.log"

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$root\src;$previousPythonPath" } else { "$root\src" }
try {
    $process = Start-Process -FilePath $PythonPath `
        -ArgumentList @("-m", "uvicorn", "aipinho.apps.bootstrap_control_main:app", "--host", $HostName, "--port", "$Port") `
        -WorkingDirectory $root `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII
$healthUrl = "http://127.0.0.1:$Port/api/v1/health"
$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) { break }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $healthy) {
    throw "AIpinho bootstrap control did not become healthy. PID=$($process.Id). Inspect $stderr"
}

Write-Output "AIpinho bootstrap control started."
Write-Output "PID: $($process.Id)"
Write-Output "Bind: $HostName`:$Port"
Write-Output "Local: $healthUrl"
Write-Output "Logs: $stdout | $stderr"
