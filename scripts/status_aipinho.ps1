[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:9088",
    [switch]$Json,
    [switch]$WriteReport
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Test-PortStatus {
    param(
        [int]$Port,
        [string]$Label,
        [string]$WhenClosed
    )
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    $status = if ($listener) { "online" } else { $WhenClosed }
    [pscustomobject]@{
        label = $Label
        port = $Port
        status = $status
        pid = if ($listener) { $listener.OwningProcess } else { $null }
    }
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Expected = "ok"
    )
    try {
        $response = Invoke-RestMethod -Uri $Url -TimeoutSec 8
        $status = if ($response.status) { [string]$response.status } else { "ok" }
        [pscustomobject]@{
            name = $Name
            url = $Url
            reachable = $true
            status = $status
            ok = $true
            error = $null
        }
    } catch {
        [pscustomobject]@{
            name = $Name
            url = $Url
            reachable = $false
            status = "offline"
            ok = $false
            error = $_.Exception.Message
        }
    }
}

$ports = @(
    Test-PortStatus -Port 9080 -Label "Bootstrap Control" -WhenClosed "offline"
    Test-PortStatus -Port 9088 -Label "Core Backend" -WhenClosed "offline"
    Test-PortStatus -Port 9089 -Label "Realtime" -WhenClosed "optional"
    Test-PortStatus -Port 9098 -Label "Artifacts Port" -WhenClosed "offline"
    Test-PortStatus -Port 9099 -Label "Monitor Supervisor" -WhenClosed "reserved"
)

$endpoints = @(
    Test-Endpoint -Name "backend_health" -Url "$BaseUrl/api/v1/health"
    Test-Endpoint -Name "health_semantics" -Url "$BaseUrl/api/v1/health/semantics"
    Test-Endpoint -Name "mobile_dashboard" -Url "$BaseUrl/api/v1/mobile/view-model/dashboard"
    Test-Endpoint -Name "mobile_debugger" -Url "$BaseUrl/api/v1/mobile/view-model/debugger"
    Test-Endpoint -Name "agents_status" -Url "$BaseUrl/api/v1/agents/status"
    Test-Endpoint -Name "runtime_hygiene_status" -Url "$BaseUrl/api/v1/runtime/hygiene/status"
)

$coreOk = ($endpoints | Where-Object { $_.name -eq "backend_health" } | Select-Object -First 1).ok
$failedRequired = @($endpoints | Where-Object { -not $_.ok -and $_.name -in @("backend_health", "health_semantics") })
$port9088 = $ports | Where-Object { $_.port -eq 9088 } | Select-Object -First 1

$overall = if (-not $coreOk -or $port9088.status -ne "online") {
    "not_ready"
} elseif ($failedRequired.Count -gt 0) {
    "ready_with_warnings"
} else {
    "ready"
}

$status = [pscustomobject]@{
    status = $overall
    generated_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    ports = $ports
    endpoints = $endpoints
    notes = @(
        "Port 9099 is a monitor/supervisor control plane and must not restart itself.",
        "Port 9080 is the minimal bootstrap control plane for restarting 9099 only.",
        "Token values and provider secrets are not printed by this script.",
        "Artifacts should be downloaded by artifact_id with Authorization header."
    )
}

if ($WriteReport) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $dir = Join-Path $root "reports\health"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $jsonPath = Join-Path $dir "health_check_$stamp.json"
    $mdPath = Join-Path $dir "health_check_$stamp.md"
    [System.IO.File]::WriteAllText($jsonPath, ($status | ConvertTo-Json -Depth 12), $Utf8NoBom)
    @(
        "# AIpinho Health Check $stamp",
        "",
        "Status: $overall",
        "Base URL: $BaseUrl",
        "",
        "## Ports",
        ""
    ) + ($ports | ForEach-Object { "- $($_.label) $($_.port): $($_.status)" }) + @(
        "",
        "## Endpoints",
        ""
    ) + ($endpoints | ForEach-Object { "- $($_.name): $($_.status) reachable=$($_.reachable)" }) |
        Set-Content -LiteralPath $mdPath -Encoding UTF8
    if (-not $Json) {
        Write-Output "Health report written:"
        Write-Output $mdPath
        Write-Output $jsonPath
    }
}

if ($Json) {
    $status | ConvertTo-Json -Depth 12
} else {
    Write-Output "AIpinho status: $overall"
    foreach ($item in $ports) {
        Write-Output ("- {0} {1}: {2}" -f $item.label, $item.port, $item.status)
    }
    foreach ($item in $endpoints) {
        Write-Output ("- {0}: {1}" -f $item.name, $item.status)
    }
}
