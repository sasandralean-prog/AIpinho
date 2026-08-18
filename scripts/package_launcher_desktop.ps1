param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$spec = Join-Path $ProjectRoot 'apps\launcher\AIpinhoLauncher.spec'

if (-not (Test-Path -LiteralPath $spec)) {
    throw "Spec file not found: $spec"
}

Push-Location $ProjectRoot
try {
    $check = & python -m PyInstaller --version 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($check)) {
        throw "PyInstaller is not installed. Install it in the active Python environment, then rerun this script."
    }
    & python -m PyInstaller $spec --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
    $exe = Join-Path $ProjectRoot 'dist\AIpinhoLauncher.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Expected executable was not generated: $exe"
    }
    Write-Output $exe
}
finally {
    Pop-Location
}
