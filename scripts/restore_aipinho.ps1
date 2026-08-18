[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupZip,
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
if (-not (Test-Path -LiteralPath $BackupZip)) {
    throw "Backup zip not found: $BackupZip"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportDir = Join-Path $root "reports\restore"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$reportPath = Join-Path $reportDir "restore_preview_$stamp.json"

$archive = [System.IO.Compression.ZipFile]::OpenRead($BackupZip)
try {
    $entries = $archive.Entries | Select-Object FullName, Length
} finally {
    $archive.Dispose()
}

$preview = [pscustomobject]@{
    status = if ($ConfirmRestore) { "blocked_manual_restore_not_implemented" } else { "preview_only" }
    created_at = (Get-Date).ToString("o")
    backup_zip = $BackupZip
    entry_count = @($entries).Count
    entries_preview = @($entries | Select-Object -First 200)
    note = "Restore is intentionally preview-only in RC3 to avoid overwriting local state without a dedicated restore plan."
}
[System.IO.File]::WriteAllText($reportPath, ($preview | ConvertTo-Json -Depth 8), $Utf8NoBom)

Write-Output "Restore preview generated:"
Write-Output $reportPath
Write-Output "No files were restored."
if ($ConfirmRestore) {
    Write-Output "ConfirmRestore was provided, but RC3 restore remains preview-only for safety."
}
