[CmdletBinding()]
param(
    [string]$PackageDir = "",
    [string]$ReleaseVerdict = "RC3_READY_FOR_LOCAL_DAILY_USE"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
if (-not $PackageDir) {
    $PackageDir = Join-Path $root "dist\aipinho_local_rc3"
}

if (Test-Path -LiteralPath $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null

$dirs = @("config", "docs", "reports", "scripts", "mobile", "launcher", "backend", "artifacts", "backups", "logs")
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir $dir) | Out-Null
}

function Copy-FileIfExists {
    param([string]$Source, [string]$Destination)
    if (Test-Path -LiteralPath $Source) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
    }
}

function Copy-DirIfExists {
    param([string]$Source, [string]$Destination)
    if (Test-Path -LiteralPath $Source) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
        Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
    }
}

function Write-Wrapper {
    param([string]$Name, [string]$Script)
    $path = Join-Path $PackageDir $Name
    @(
        "@echo off",
        "set PROJECT_ROOT=%~dp0..\..",
        "powershell -ExecutionPolicy Bypass -File ""%PROJECT_ROOT%\scripts\$Script"" %*"
    ) | Set-Content -LiteralPath $path -Encoding ASCII
}

function Copy-SanitizedConfig {
    $sourceRoot = Join-Path $root "config"
    $targetRoot = Join-Path $PackageDir "config"
    if (-not (Test-Path -LiteralPath $sourceRoot)) { return @() }
    $copied = [System.Collections.Generic.List[string]]::new()
    Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart("\")
        $target = Join-Path $targetRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        $text = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
        if ($null -eq $text) { return }
        $text = $text -replace '(?im)^(\s*[^#\r\n]*(api_key|token|secret|password|authorization|bearer)[^:\r\n]*:\s*).+$', '$1[REDACTED]'
        $text = $text -replace '(?im)(AIza[0-9A-Za-z_\-]{20,})', '[REDACTED_API_KEY]'
        $text = $text -replace '(?im)(sk-[0-9A-Za-z_\-]{20,})', '[REDACTED_API_KEY]'
        Set-Content -LiteralPath $target -Value $text -Encoding UTF8
        $copied.Add($relative)
    }
    return @($copied)
}

Copy-FileIfExists (Join-Path $root "README_FIRST_RUN.md") (Join-Path $PackageDir "README_FIRST_RUN.md")
Copy-FileIfExists (Join-Path $root "README_OPERATIONAL.md") (Join-Path $PackageDir "README_OPERATIONAL.md")
Copy-FileIfExists (Join-Path $root "RELEASE_NOTES_RC3.md") (Join-Path $PackageDir "RELEASE_NOTES_RC3.md")
Copy-DirIfExists (Join-Path $root "docs") (Join-Path $PackageDir "docs")
Copy-DirIfExists (Join-Path $root "reports\release") (Join-Path $PackageDir "reports\release")
Copy-DirIfExists (Join-Path $root "reports\health") (Join-Path $PackageDir "reports\health")
Copy-DirIfExists (Join-Path $root "reports\regression") (Join-Path $PackageDir "reports\regression")
Copy-DirIfExists (Join-Path $root "scripts") (Join-Path $PackageDir "scripts")
Copy-DirIfExists (Join-Path $root "artifacts") (Join-Path $PackageDir "artifacts")

$apk = Join-Path $root "apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk"
if (Test-Path -LiteralPath $apk) {
    Copy-Item -LiteralPath $apk -Destination (Join-Path $PackageDir "mobile\aipinho-mobile-rc3.apk") -Force
}

$launcherExe = Join-Path $root "dist\AIpinhoLauncher.exe"
if (Test-Path -LiteralPath $launcherExe) {
    Copy-Item -LiteralPath $launcherExe -Destination (Join-Path $PackageDir "launcher\AIpinhoLauncher.exe") -Force
}
Copy-DirIfExists (Join-Path $root "apps\launcher") (Join-Path $PackageDir "launcher\source")

$configFiles = Copy-SanitizedConfig

Write-Wrapper -Name "START_AIPINHO.bat" -Script "start_aipinho.ps1"
Write-Wrapper -Name "STOP_AIPINHO.bat" -Script "stop_aipinho.ps1"
Write-Wrapper -Name "STATUS_AIPINHO.bat" -Script "status_aipinho.ps1"
Write-Wrapper -Name "DOCTOR_AIPINHO.bat" -Script "doctor_aipinho.ps1"
Write-Wrapper -Name "OPEN_LAUNCHER.bat" -Script "open_launcher.ps1"

$status = $null
try {
    $status = (& (Join-Path $root "scripts\status_aipinho.ps1") -Json | ConvertFrom-Json)
} catch {
    $status = [pscustomobject]@{ status = "unknown"; error = $_.Exception.Message }
}

$manifest = [pscustomobject]@{
    version = "rc3"
    build_timestamp = (Get-Date).ToString("o")
    git_commit = $null
    included_components = @("backend scripts", "mobile apk when available", "launcher executable/source", "docs", "reports", "sanitized config", "artifact index")
    backend_status = $status
    mobile_apk_path = "mobile\aipinho-mobile-rc3.apk"
    launcher_path = if (Test-Path -LiteralPath (Join-Path $PackageDir "launcher\AIpinhoLauncher.exe")) { "launcher\AIpinhoLauncher.exe" } else { "scripts\open_launcher.ps1" }
    config_files = $configFiles
    docs = @("README_FIRST_RUN.md", "README_OPERATIONAL.md", "docs\operations", "docs\mobile", "docs\desktop", "docs\release")
    reports = @("reports\health", "reports\release", "reports\regression")
    known_issues = @("docs\operations\KNOWN_ISSUES.md", "docs\release\RC3_KNOWN_ISSUES.md")
    generated_by = "Codex"
    release_verdict = $ReleaseVerdict
    secrets_included = $false
}

$manifestPath = Join-Path $PackageDir "RELEASE_MANIFEST.json"
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 20), $Utf8NoBom)

Write-Output "RC3 package generated:"
Write-Output $PackageDir
Write-Output $manifestPath
