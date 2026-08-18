[CmdletBinding()]
param(
    [switch]$ApplyAdbReverse
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$ports = @(9080, 9088, 9089, 9098, 9099)

Write-Output "AIpinho mobile pairing preparation"
Write-Output ""
Write-Output "Official ports:"
$ports | ForEach-Object { Write-Output "- tcp:$_" }
Write-Output ""
Write-Output "ADB reverse commands:"
$ports | ForEach-Object { Write-Output "adb reverse tcp:$_ tcp:$_" }
Write-Output ""
Write-Output "LAN/Tailscale:"
Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    ForEach-Object { Write-Output "- $($_.InterfaceAlias): http://$($_.IPAddress):9088/api/v1/health" }
Write-Output ""
Write-Output "Token values are never printed by this script."

if ($ApplyAdbReverse) {
    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if (-not $adb) {
        throw "adb not found in PATH. Install Android platform-tools or set PATH before using -ApplyAdbReverse."
    }
    foreach ($port in $ports) {
        & $adb.Source reverse "tcp:$port" "tcp:$port"
    }
    Write-Output "ADB reverse applied for official AIpinho ports."
}
