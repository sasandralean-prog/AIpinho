[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$exe = Join-Path $root "dist\AIpinhoLauncher.exe"
$script = Join-Path $root "scripts\dev\start_launcher_desktop.ps1"

if (Test-Path -LiteralPath $exe) {
    Write-Output "Opening AIpinho Launcher executable..."
    Start-Process -FilePath $exe -WorkingDirectory $root
    exit 0
}

if (Test-Path -LiteralPath $script) {
    Write-Output "Opening AIpinho Launcher through Python script..."
    & $script -ProjectRoot $root
    exit 0
}

throw "Launcher entrypoint not found. Expected dist\AIpinhoLauncher.exe or scripts\dev\start_launcher_desktop.ps1."

