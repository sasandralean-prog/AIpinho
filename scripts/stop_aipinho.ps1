[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 9088
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$stopScript = Join-Path $root "scripts\dev\stop_aipinho_9088.ps1"

Write-Output "Stopping AIpinho core backend on port $Port..."
& $stopScript -Port $Port
Write-Output "AIpinho core stop request finished. Port 9099 is not restarted or stopped by this script."

