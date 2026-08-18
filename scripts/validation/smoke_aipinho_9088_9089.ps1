[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 9088,
    [ValidateRange(1, 65535)]
    [int]$AuxiliaryPort = 9089
)

$ErrorActionPreference = "Stop"
$results = [System.Collections.Generic.List[object]]::new()

function Test-AIpinhoHealth {
    param([string]$Label, [string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8
        $results.Add([pscustomobject]@{ Target = $Label; Url = $Url; Status = $response.StatusCode; Ok = ($response.StatusCode -eq 200); Error = $null })
    } catch {
        $results.Add([pscustomobject]@{ Target = $Label; Url = $Url; Status = $null; Ok = $false; Error = $_.Exception.Message })
    }
}

Test-AIpinhoHealth -Label "localhost" -Url "http://127.0.0.1:$ApiPort/api/v1/health"
$addresses = Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
$lan = $addresses | Where-Object { $_.InterfaceAlias -notmatch "Tailscale|Loopback" -and ($_.IPAddress -like "10.*" -or $_.IPAddress -like "192.168.*" -or $_.IPAddress -match "^172\.(1[6-9]|2[0-9]|3[01])\.") }
$tailscale = $addresses | Where-Object { $_.InterfaceAlias -match "Tailscale" -or $_.IPAddress -like "100.*" }
foreach ($item in $lan) { Test-AIpinhoHealth -Label "LAN/$($item.InterfaceAlias)" -Url "http://$($item.IPAddress):$ApiPort/api/v1/health" }
foreach ($item in $tailscale) { Test-AIpinhoHealth -Label "Tailscale/$($item.InterfaceAlias)" -Url "http://$($item.IPAddress):$ApiPort/api/v1/health" }

$auxListener = Get-NetTCPConnection -State Listen -LocalPort $AuxiliaryPort -ErrorAction SilentlyContinue | Select-Object -First 1
$rules = Get-NetFirewallRule -DisplayName "AIpinho*" -ErrorAction SilentlyContinue
$results | Format-Table -AutoSize
Write-Output "Auxiliary port $AuxiliaryPort listener: $(if ($auxListener) { 'active' } else { 'reserved/no service' })"
Write-Output "Persistent AIpinho firewall rules: $(@($rules).Count)"

if (@($results | Where-Object { -not $_.Ok }).Count -gt 0) {
    throw "One or more AIpinho API health checks failed."
}
