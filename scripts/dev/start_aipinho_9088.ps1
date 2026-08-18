[CmdletBinding()]
param(
    [string]$HostName = "0.0.0.0",
    [ValidateRange(1, 65535)]
    [int]$Port = 9088,
    [string]$PythonPath = "",
    [int]$StartupTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path

$approvedUserEnvironment = @(
    "GEMINI_API_KEY_PRIMARY",
    "GEMINI_API_KEY_SECONDARY",
    "GEMINI_EXECUTOR_ENABLED",
    "CODEX_AGENT_ENABLED"
)
foreach ($name in $approvedUserEnvironment) {
    if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
        $userValue = [Environment]::GetEnvironmentVariable($name, "User")
        if ($userValue) {
            [Environment]::SetEnvironmentVariable($name, $userValue, "Process")
        }
    }
}

if (-not $PSBoundParameters.ContainsKey("HostName") -and $env:AIPINHO_HOST) {
    $HostName = $env:AIPINHO_HOST
}
if (-not $PSBoundParameters.ContainsKey("Port") -and $env:AIPINHO_PORT) {
    $Port = [int]$env:AIPINHO_PORT
}
if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
    $healthIdentifiesAipinho = $false
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 3
        $healthIdentifiesAipinho = $health.service -eq "AIpinho"
    } catch {
        $healthIdentifiesAipinho = $false
    }
    if ($owner -and (($owner.CommandLine -match "aipinho\.main:app") -or $healthIdentifiesAipinho)) {
        Write-Output "AIpinho API already listening on port $Port (PID $($listener.OwningProcess))."
        exit 0
    }
    throw "Port $Port is already used by PID $($listener.OwningProcess); refusing to replace an unrelated process."
}

$runtimeDir = Join-Path $root "data\runtime"
$logDir = Join-Path $root "data\logs\runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir,$logDir | Out-Null
$pidFile = Join-Path $runtimeDir "aipinho_api_$Port.pid"
$stdout = Join-Path $logDir "aipinho_api_$Port.out.log"
$stderr = Join-Path $logDir "aipinho_api_$Port.err.log"

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($previousPythonPath) { "$root\src;$previousPythonPath" } else { "$root\src" }
try {
    $process = Start-Process -FilePath $PythonPath `
        -ArgumentList @("-m", "uvicorn", "aipinho.main:app", "--host", $HostName, "--port", "$Port") `
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
    throw "AIpinho API did not become healthy. PID=$($process.Id). Inspect $stderr"
}

$addresses = Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
$lan = $addresses | Where-Object { $_.InterfaceAlias -notmatch "Tailscale|Loopback" -and ($_.IPAddress -like "10.*" -or $_.IPAddress -like "192.168.*" -or $_.IPAddress -match "^172\.(1[6-9]|2[0-9]|3[01])\.") }
$tailscale = $addresses | Where-Object { $_.InterfaceAlias -match "Tailscale" -or $_.IPAddress -like "100.*" }

Write-Output "AIpinho API started."
Write-Output "PID: $($process.Id)"
Write-Output "Bind: $HostName`:$Port"
Write-Output "Local: $healthUrl"
foreach ($item in $lan) { Write-Output "LAN: http://$($item.IPAddress):$Port/api/v1/health" }
foreach ($item in $tailscale) { Write-Output "Tailscale: http://$($item.IPAddress):$Port/api/v1/health" }
Write-Output "Logs: $stdout | $stderr"
