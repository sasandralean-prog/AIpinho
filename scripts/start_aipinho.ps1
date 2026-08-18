[CmdletBinding()]
param(
    [string]$HostName = "0.0.0.0",
    [ValidateRange(1, 65535)]
    [int]$Port = 9088
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$startScript = Join-Path $root "scripts\dev\start_aipinho_9088.ps1"

Write-Output "Starting AIpinho core backend on port $Port..."
& $startScript -HostName $HostName -Port $Port
Write-Output ""
Write-Output "Status after start:"
& (Join-Path $root "scripts\status_aipinho.ps1")

