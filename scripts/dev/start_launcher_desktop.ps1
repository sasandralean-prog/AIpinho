param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\src"
    & python -m apps.launcher.ui.launcher_ui_main
}
finally {
    Pop-Location
}
