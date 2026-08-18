[CmdletBinding()]
param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
if (-not $OutputDir) {
    $OutputDir = Join-Path $root "backups"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stage = Join-Path $OutputDir "aipinho_backup_$stamp.stage"
$zipPath = Join-Path $OutputDir "aipinho_backup_$stamp.zip"
$manifestPath = Join-Path $OutputDir "aipinho_backup_$stamp.json"

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

function Copy-IfExists {
    param([string]$RelativePath)
    $src = Join-Path $root $RelativePath
    if (Test-Path -LiteralPath $src) {
        $dst = Join-Path $stage $RelativePath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
    }
}

function Copy-SanitizedConfig {
    $configRoot = Join-Path $root "config"
    $targetRoot = Join-Path $stage "config_sanitized"
    if (-not (Test-Path -LiteralPath $configRoot)) { return }
    Get-ChildItem -LiteralPath $configRoot -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($configRoot.Length).TrimStart("\")
        $target = Join-Path $targetRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        $text = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
        if ($null -eq $text) { return }
        $text = $text -replace '(?im)^(\s*[^#\r\n]*(api_key|token|secret|password|authorization|bearer)[^:\r\n]*:\s*).+$', '$1[REDACTED]'
        $text = $text -replace '(?im)(AIza[0-9A-Za-z_\-]{20,})', '[REDACTED_API_KEY]'
        $text = $text -replace '(?im)(sk-[0-9A-Za-z_\-]{20,})', '[REDACTED_API_KEY]'
        Set-Content -LiteralPath $target -Value $text -Encoding UTF8
    }
}

Copy-IfExists "docs"
Copy-IfExists "reports"
Copy-IfExists "data\artifacts"
Copy-IfExists "data\runtime\agents"
Copy-IfExists "data\runtime\hygiene"
Copy-SanitizedConfig

$manifest = [pscustomobject]@{
    backup_id = "aipinho_backup_$stamp"
    created_at = (Get-Date).ToString("o")
    root = $root
    zip_path = $zipPath
    includes = @("docs", "reports", "data/artifacts", "data/runtime/agents", "data/runtime/hygiene", "config_sanitized")
    excludes = @("provider secrets", "bearer token values", "raw unsanitized logs", "cache directories")
    secrets_redacted = $true
}
$stageManifest = Join-Path $stage "BACKUP_MANIFEST.json"
[System.IO.File]::WriteAllText($stageManifest, ($manifest | ConvertTo-Json -Depth 8), $Utf8NoBom)

if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), $Utf8NoBom)
Remove-Item -LiteralPath $stage -Recurse -Force

Write-Output "Backup created:"
Write-Output $zipPath
Write-Output $manifestPath
