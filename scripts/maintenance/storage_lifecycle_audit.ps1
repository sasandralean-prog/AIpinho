param(
    [string[]]$AuditRoots = @("C:\Users\rafae\Documents", "C:\Dev\AIpinho"),
    [string]$TrashRoot = "D:\rafa\AIlixo",
    [string]$ArchiveRoot = "D:\rafa\AICodex",
    [string]$AipinhoQuarantineRoot = "D:\rafa\AIpinhoQuarantine",
    [string]$ReportRoot = "C:\Dev\AIpinho\reports\storage",
    [string]$ActiveCodexWorkspace = "",
    [switch]$DryRun,
    [switch]$FastDuplicateScan,
    [int64]$MaxHashBytes = 1073741824,
    [int64]$MaxDuplicateHashBytes = 536870912
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$now = Get-Date
$runStamp = $now.ToString("yyyyMMdd_HHmmss")
$classifications = @("KEEP", "ARCHIVE", "SAFE_TO_DELETE", "NEEDS_REVIEW")

function New-DirectoryIfMissing {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-FullPathSafe {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Test-PathStartsWith {
    param([string]$Path, [string]$Root)
    $fullPath = (Get-FullPathSafe $Path).TrimEnd('\')
    $fullRoot = (Get-FullPathSafe $Root).TrimEnd('\')
    return $fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        $fullPath.StartsWith($fullRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-RelativePathSafe {
    param([string]$Root, [string]$Path)
    $rootFull = (Get-FullPathSafe $Root).TrimEnd('\') + "\"
    $pathFull = Get-FullPathSafe $Path
    if ($pathFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $pathFull.Substring($rootFull.Length)
    }
    return (Split-Path -Leaf $Path)
}

function ConvertTo-SafeDestination {
    param(
        [string]$OriginalPath,
        [string]$SourceRoot,
        [string]$DestinationRoot,
        [string]$RootLabel
    )
    $relative = Get-RelativePathSafe -Root $SourceRoot -Path $OriginalPath
    $destination = Join-Path (Join-Path $DestinationRoot $RootLabel) $relative
    $destinationFull = Get-FullPathSafe $destination
    $destinationRootFull = Get-FullPathSafe $DestinationRoot
    if (-not (Test-PathStartsWith -Path $destinationFull -Root $destinationRootFull)) {
        throw "destination_outside_root: $destinationFull"
    }
    return $destinationFull
}

function Get-UniqueDestination {
    param([string]$Destination)
    if (-not (Test-Path -LiteralPath $Destination)) {
        return $Destination
    }
    $dir = Split-Path -Parent $Destination
    $name = [System.IO.Path]::GetFileNameWithoutExtension($Destination)
    $ext = [System.IO.Path]::GetExtension($Destination)
    $candidate = Join-Path $dir ("{0}.moved_{1}{2}" -f $name, $runStamp, $ext)
    $i = 1
    while (Test-Path -LiteralPath $candidate) {
        $candidate = Join-Path $dir ("{0}.moved_{1}_{2}{3}" -f $name, $runStamp, $i, $ext)
        $i++
    }
    return $candidate
}

function Get-Sha256IfApplicable {
    param([System.IO.FileInfo]$File)
    if ($File.Length -gt $MaxHashBytes) {
        return $null
    }
    try {
        return (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
    } catch {
        return $null
    }
}

function Split-PathSegments {
    param([string]$Path)
    return ((Get-FullPathSafe $Path) -split '[\\/]') | Where-Object { $_ -ne "" }
}

function Get-FilesStreaming {
    param(
        [string]$Root,
        [System.Collections.Generic.List[object]]$Errors
    )
    $stack = New-Object "System.Collections.Generic.Stack[System.IO.DirectoryInfo]"
    $stack.Push([System.IO.DirectoryInfo]::new($Root))
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        try {
            foreach ($file in $dir.EnumerateFiles()) {
                if (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) {
                    Write-Output $file
                }
            }
        } catch {
            $Errors.Add([pscustomobject][ordered]@{ path = $dir.FullName; error = "enumerate_files_failed: $($_.Exception.Message)" })
        }
        try {
            foreach ($child in $dir.EnumerateDirectories()) {
                if (($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) {
                    $stack.Push($child)
                }
            }
        } catch {
            $Errors.Add([pscustomobject][ordered]@{ path = $dir.FullName; error = "enumerate_directories_failed: $($_.Exception.Message)" })
        }
    }
}

function Test-Segment {
    param([string[]]$Segments, [string[]]$Names)
    foreach ($segment in $Segments) {
        foreach ($name in $Names) {
            if ($segment.Equals($name, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        }
    }
    return $false
}

function Test-UnderRelativePrefix {
    param([string]$RelativePath, [string[]]$Prefixes)
    $rel = $RelativePath.Replace("/", "\").TrimStart("\")
    foreach ($prefix in $Prefixes) {
        $p = $prefix.Trim("\")
        if ($rel.Equals($p, [System.StringComparison]::OrdinalIgnoreCase) -or
            $rel.StartsWith($p + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-Classification {
    param(
        [System.IO.FileInfo]$File,
        [string]$Root,
        [string]$RootKind,
        [string]$RelativePath
    )

    $path = $File.FullName
    $pathLower = $path.ToLowerInvariant()
    $segments = Split-PathSegments $path
    $ext = $File.Extension.ToLowerInvariant()
    $ageDays = [math]::Floor(($now - $File.LastWriteTime).TotalDays)
    $accessAgeDays = [math]::Floor(($now - $File.LastAccessTime).TotalDays)
    $size = $File.Length

    $result = [ordered]@{
        classification = "KEEP"
        reason = "default_keep_conservative"
        destination_kind = $null
    }

    if ($ActiveCodexWorkspace -and (Test-PathStartsWith -Path $path -Root $ActiveCodexWorkspace)) {
        $result.classification = "KEEP"
        $result.reason = "active_codex_workspace"
        return $result
    }

    if (Test-Segment -Segments $segments -Names @(".git")) {
        $result.classification = "KEEP"
        $result.reason = "git_repository_internal"
        return $result
    }

    if ($ext -in @(".gguf", ".safetensors", ".onnx", ".pt", ".pth")) {
        $result.classification = "NEEDS_REVIEW"
        $result.reason = "model_or_ml_weight_never_moved_automatically"
        return $result
    }

    if ($ext -in @(".db", ".sqlite", ".sqlite3", ".mdb", ".idx", ".index", ".faiss")) {
        $result.classification = "NEEDS_REVIEW"
        $result.reason = "database_or_index_requires_manual_review"
        return $result
    }

    if ($size -gt 1073741824 -and $ext -notin @(".zip", ".7z", ".rar", ".apk", ".aab", ".log", ".tmp")) {
        $result.classification = "NEEDS_REVIEW"
        $result.reason = "large_unknown_file_requires_review"
        return $result
    }

    $generatedSegments = @("node_modules", ".gradle", ".m2", "build", "dist", "out", "target", "coverage", ".pytest_cache", "__pycache__", ".next", ".expo", ".cxx", "obj", "bin")
    $tempSegments = @("cache", "caches", "tmp", "temp", "temporary")
    $runtimeSegments = @("task_runs", "approvals", "events", "sessions", "session_grants", "raw", "traces")
    $generatedExt = @(".tmp", ".temp", ".cache", ".log", ".bak", ".old", ".orig", ".pid", ".dmp", ".dump", ".trace")
    $archiveExt = @(".zip", ".7z", ".rar", ".apk", ".aab", ".logcat", ".har")
    $mediaEvidenceExt = @(".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov")
    $sourceExt = @(".py", ".ps1", ".bat", ".cmd", ".kt", ".java", ".js", ".ts", ".tsx", ".jsx", ".cs", ".sln", ".csproj", ".gradle", ".kts", ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".xml")

    if ($RootKind -eq "AIpinho") {
        if (Test-UnderRelativePrefix -RelativePath $RelativePath -Prefixes @("reports\storage")) {
            $result.classification = "KEEP"
            $result.reason = "current_storage_audit_report"
            return $result
        }

        $protectedPrefixes = @("src", "config", "policies", "contracts", "templates", "skills", "prompts", "tests", "scripts")
        if (Test-UnderRelativePrefix -RelativePath $RelativePath -Prefixes $protectedPrefixes) {
            $result.classification = "KEEP"
            $result.reason = "aipinho_source_or_operational_asset"
            return $result
        }

        if (Test-UnderRelativePrefix -RelativePath $RelativePath -Prefixes @("data\runtime")) {
            if ($ageDays -lt 7) {
                $result.classification = "KEEP"
                $result.reason = "recent_runtime_state"
                return $result
            }
            if (Test-Segment -Segments $segments -Names $runtimeSegments) {
                if ($ageDays -ge 30) {
                    $result.classification = "ARCHIVE"
                    $result.reason = "old_runtime_state_quarantine_reversible"
                    $result.destination_kind = "AIpinhoQuarantine"
                    return $result
                }
                $result.classification = "NEEDS_REVIEW"
                $result.reason = "runtime_state_not_recent_enough_to_keep_but_not_old_enough_to_archive"
                return $result
            }
            $result.classification = "NEEDS_REVIEW"
            $result.reason = "runtime_data_requires_manual_review"
            return $result
        }

        if (Test-UnderRelativePrefix -RelativePath $RelativePath -Prefixes @("data\logs", "reports", "artifacts", "exports", "screenshots", "downloads")) {
            if ($ageDays -ge 14 -or ($size -gt 52428800 -and $ageDays -ge 7)) {
                $result.classification = "ARCHIVE"
                $result.reason = "old_aipinho_generated_evidence_or_log"
                $result.destination_kind = "AIpinhoQuarantine"
                return $result
            }
            $result.classification = "KEEP"
            $result.reason = "recent_aipinho_generated_evidence_or_log"
            return $result
        }

        if ((Test-Segment -Segments $segments -Names ($generatedSegments + $tempSegments)) -and $ageDays -ge 14) {
            $result.classification = "SAFE_TO_DELETE"
            $result.reason = "old_aipinho_cache_or_build_output_reversible_quarantine"
            $result.destination_kind = "Trash"
            return $result
        }

        if ($ext -in $generatedExt -and $ageDays -ge 14) {
            $result.classification = "ARCHIVE"
            $result.reason = "old_aipinho_generated_text_log_or_backup"
            $result.destination_kind = "AIpinhoQuarantine"
            return $result
        }

        $result.classification = "KEEP"
        $result.reason = "aipinho_unclassified_conservative_keep"
        return $result
    }

    if ((Test-Segment -Segments $segments -Names ($generatedSegments + $tempSegments)) -and $ageDays -ge 14) {
        $result.classification = "SAFE_TO_DELETE"
        $result.reason = "old_generated_cache_build_or_dependency_output"
        $result.destination_kind = "Trash"
        return $result
    }

    if ($ext -in @(".tmp", ".temp", ".cache", ".dmp", ".dump", ".trace") -and $ageDays -ge 7) {
        $result.classification = "SAFE_TO_DELETE"
        $result.reason = "old_temporary_or_dump_file"
        $result.destination_kind = "Trash"
        return $result
    }

    if ($ext -eq ".log" -and $ageDays -ge 14) {
        $result.classification = "SAFE_TO_DELETE"
        $result.reason = "old_log_file"
        $result.destination_kind = "Trash"
        return $result
    }

    if ($ext -in @(".bak", ".old", ".orig") -and $ageDays -ge 30) {
        $result.classification = "ARCHIVE"
        $result.reason = "old_backup_file_preserved"
        $result.destination_kind = "Archive"
        return $result
    }

    $evidencePathSignal = Test-Segment -Segments $segments -Names @("reports", "report", "artifacts", "artifact", "exports", "export", "screenshots", "screenshot", "logcat", "logs", "downloads", "builds", "releases")
    if (($ext -in $archiveExt -or ($ext -in $mediaEvidenceExt -and $evidencePathSignal)) -and $ageDays -ge 30) {
        $result.classification = "ARCHIVE"
        $result.reason = "old_archive_apk_screenshot_export_or_evidence"
        $result.destination_kind = "Archive"
        return $result
    }

    if ($evidencePathSignal -and $ageDays -ge 60 -and $ext -in @(".json", ".md", ".txt", ".csv", ".html", ".xml")) {
        $result.classification = "ARCHIVE"
        $result.reason = "old_report_trace_or_export_metadata"
        $result.destination_kind = "Archive"
        return $result
    }

    if ($ext -in $sourceExt) {
        $result.classification = "KEEP"
        $result.reason = "source_config_or_documentation_file"
        return $result
    }

    if ($ageDays -ge 180 -and $accessAgeDays -ge 90 -and $size -gt 104857600) {
        $result.classification = "NEEDS_REVIEW"
        $result.reason = "old_large_unknown_file_manual_review"
        return $result
    }

    $result.classification = "KEEP"
    $result.reason = "documents_unclassified_conservative_keep"
    return $result
}

function Write-Json {
    param([object]$Value, [string]$Path, [int]$Depth = 8)
    $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Format-Bytes {
    param([int64]$Bytes)
    if ($Bytes -ge 1TB) { return "{0:N2} TB" -f ($Bytes / 1TB) }
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

function Sum-ItemSize {
    param([object]$Items)
    $total = [int64]0
    foreach ($item in $Items) {
        if ($null -ne $item -and $null -ne $item.size) {
            $total += [int64]$item.size
        }
    }
    return $total
}

function Write-MarkdownList {
    param(
        [string]$Path,
        [string]$Title,
        [object[]]$Items
    )
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# $Title")
    $lines.Add("")
    $lines.Add("Generated: $($now.ToString("o"))")
    $lines.Add("")
    $lines.Add("Count: $($Items.Count)")
    $lines.Add("")
    $lines.Add("| Classification | Size | Age days | Reason | Path | Destination |")
    $lines.Add("|---|---:|---:|---|---|---|")
    foreach ($item in $Items) {
        $dest = if ($item.new_path) { $item.new_path } else { "" }
        $reason = ($item.reason -replace "\|", "/")
        $pathText = ($item.path -replace "\|", "/")
        $destText = ($dest -replace "\|", "/")
        $lines.Add("| $($item.classification) | $(Format-Bytes $item.size) | $($item.age_days) | $reason | $pathText | $destText |")
    }
    $lines | Set-Content -LiteralPath $Path -Encoding UTF8
}

New-DirectoryIfMissing -Path $TrashRoot
New-DirectoryIfMissing -Path $ArchiveRoot
New-DirectoryIfMissing -Path $AipinhoQuarantineRoot
New-DirectoryIfMissing -Path $ReportRoot

$resolvedRoots = @()
foreach ($root in $AuditRoots) {
    if (Test-Path -LiteralPath $root) {
        $resolvedRoots += (Get-FullPathSafe $root).TrimEnd('\')
    }
}
if ($resolvedRoots.Count -eq 0) {
    throw "no_audit_roots_found"
}

$inventory = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[object]

foreach ($root in $resolvedRoots) {
    $rootKind = if ($root.Equals((Get-FullPathSafe "C:\Dev\AIpinho").TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) { "AIpinho" } else { "Documents" }
    $rootLabel = if ($rootKind -eq "AIpinho") { "AIpinho" } else { "Documents" }
    foreach ($file in (Get-FilesStreaming -Root $root -Errors $errors)) {
        try {
            if (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                continue
            }
            $relative = Get-RelativePathSafe -Root $root -Path $file.FullName
            $decision = Get-Classification -File $file -Root $root -RootKind $rootKind -RelativePath $relative
            $destinationRoot = $null
            if ($decision.classification -eq "SAFE_TO_DELETE") {
                $destinationRoot = $TrashRoot
            } elseif ($decision.classification -eq "ARCHIVE") {
                $destinationRoot = if ($decision.destination_kind -eq "AIpinhoQuarantine" -or $rootKind -eq "AIpinho") { $AipinhoQuarantineRoot } else { $ArchiveRoot }
            }
            $newPath = $null
            if ($destinationRoot) {
                $newPath = ConvertTo-SafeDestination -OriginalPath $file.FullName -SourceRoot $root -DestinationRoot $destinationRoot -RootLabel $rootLabel
                $newPath = Get-UniqueDestination -Destination $newPath
            }
            $inventory.Add([pscustomobject][ordered]@{
                path = $file.FullName
                root = $root
                root_kind = $rootKind
                relative_path = $relative
                classification = $decision.classification
                reason = $decision.reason
                size = [int64]$file.Length
                extension = $file.Extension.ToLowerInvariant()
                created_at = $file.CreationTimeUtc.ToString("o")
                modified_at = $file.LastWriteTimeUtc.ToString("o")
                accessed_at = $file.LastAccessTimeUtc.ToString("o")
                age_days = [int][math]::Floor(($now - $file.LastWriteTime).TotalDays)
                access_age_days = [int][math]::Floor(($now - $file.LastAccessTime).TotalDays)
                new_path = $newPath
                moved = $false
                move_error = $null
            })
        } catch {
            $errors.Add([pscustomobject][ordered]@{ path = $file.FullName; error = $_.Exception.Message })
        }
    }
}

$beforeBytes = Sum-ItemSize -Items $inventory

$duplicateGroups = New-Object System.Collections.Generic.List[object]
$hashCache = @{}
if ($FastDuplicateScan) {
    $probableGroups = $inventory |
        Where-Object { $_.size -gt 1048576 -and $_.classification -ne "KEEP" } |
        Group-Object -Property @{ Expression = { "{0}|{1}" -f $_.size, (Split-Path -Leaf $_.path).ToLowerInvariant() } } |
        Where-Object { $_.Count -gt 1 }
    foreach ($group in $probableGroups) {
        $first = $group.Group | Select-Object -First 1
        $duplicateGroups.Add([pscustomobject][ordered]@{
            hash = $null
            duplicate_detection = "probable_name_and_size_fast_scan"
            size = [int64]$first.size
            count = $group.Count
            files = @($group.Group | ForEach-Object { $_.path })
        })
    }
} else {
    $sizeGroups = $inventory |
        Where-Object { $_.size -gt 1048576 -and $_.size -le $MaxDuplicateHashBytes -and $_.classification -ne "KEEP" } |
        Group-Object -Property size |
        Where-Object { $_.Count -gt 1 }

    foreach ($group in $sizeGroups) {
        $hashGroups = @{}
        foreach ($item in $group.Group) {
            try {
                $hash = (Get-FileHash -LiteralPath $item.path -Algorithm SHA256 -ErrorAction Stop).Hash
                $hashCache[$item.path] = $hash
                if (-not $hashGroups.ContainsKey($hash)) {
                    $hashGroups[$hash] = New-Object System.Collections.Generic.List[object]
                }
                $hashGroups[$hash].Add($item)
            } catch {
                $errors.Add([pscustomobject][ordered]@{ path = $item.path; error = "duplicate_hash_failed: $($_.Exception.Message)" })
            }
        }
        foreach ($hash in $hashGroups.Keys) {
            if ($hashGroups[$hash].Count -gt 1) {
                $duplicateGroups.Add([pscustomobject][ordered]@{
                    hash = $hash
                    duplicate_detection = "sha256"
                    size = [int64]$group.Name
                    count = $hashGroups[$hash].Count
                    files = @($hashGroups[$hash] | ForEach-Object { $_.path })
                })
            }
        }
    }
}

$manifest = New-Object System.Collections.Generic.List[object]
$moveCandidates = @($inventory | Where-Object { $_.classification -in @("ARCHIVE", "SAFE_TO_DELETE") -and $_.new_path })
foreach ($item in $moveCandidates) {
    try {
        $source = $item.path
        if (-not (Test-Path -LiteralPath $source)) {
            $item.moved = $false
            $item.move_error = "source_missing_before_move"
            continue
        }
        $fileInfo = Get-Item -LiteralPath $source -Force
        $hash = if ($hashCache.ContainsKey($source)) { $hashCache[$source] } else { Get-Sha256IfApplicable -File $fileInfo }
        if (-not $DryRun) {
            New-DirectoryIfMissing -Path (Split-Path -Parent $item.new_path)
            Move-Item -LiteralPath $source -Destination $item.new_path -Force -ErrorAction Stop
        }
        $item.moved = -not $DryRun
        $manifest.Add([pscustomobject][ordered]@{
            original_path = $source
            new_path = $item.new_path
            reason = $item.reason
            classification = $item.classification
            size = [int64]$item.size
            date = $now.ToString("o")
            hash_sha256 = $hash
            dry_run = [bool]$DryRun
        })
    } catch {
        $item.moved = $false
        $item.move_error = $_.Exception.Message
        $item.classification = "NEEDS_REVIEW"
        $item.reason = "move_failed_requires_review"
    }
}

$movedItems = @($inventory | Where-Object { $_.moved -eq $true })
$movedBytes = Sum-ItemSize -Items $movedItems
$afterBytes = $beforeBytes - $movedBytes

$keepItems = @($inventory | Where-Object { $_.classification -eq "KEEP" })
$archiveItems = @($inventory | Where-Object { $_.classification -eq "ARCHIVE" })
$safeItems = @($inventory | Where-Object { $_.classification -eq "SAFE_TO_DELETE" })
$reviewItems = @($inventory | Where-Object { $_.classification -eq "NEEDS_REVIEW" })

$summary = [ordered]@{
    generated_at = $now.ToString("o")
    dry_run = [bool]$DryRun
    audit_roots = $resolvedRoots
    destinations = [ordered]@{
        trash = $TrashRoot
        archive = $ArchiveRoot
        aipinho_quarantine = $AipinhoQuarantineRoot
    }
    total_files_audited = $inventory.Count
    space_used_before_bytes = $beforeBytes
    space_used_after_bytes = $afterBytes
    space_moved_or_recovered_bytes = $movedBytes
    space_used_before_human = Format-Bytes $beforeBytes
    space_used_after_human = Format-Bytes $afterBytes
    space_moved_or_recovered_human = Format-Bytes $movedBytes
    moved_files = $movedItems.Count
    archive_count = ($movedItems | Where-Object { $_.classification -eq "ARCHIVE" }).Count
    safe_to_delete_count = ($movedItems | Where-Object { $_.classification -eq "SAFE_TO_DELETE" }).Count
    kept_count = $keepItems.Count
    needs_review_count = $reviewItems.Count
    duplicate_groups = $duplicateGroups.Count
    errors_count = $errors.Count
}

Write-Json -Value $inventory -Path (Join-Path $ReportRoot "storage_inventory.json") -Depth 8
Write-Json -Value $manifest -Path (Join-Path $ReportRoot "storage_manifest.json") -Depth 8
Write-Json -Value ([ordered]@{ summary = $summary; duplicates = $duplicateGroups; errors = $errors }) -Path (Join-Path $ReportRoot "storage_duplicates.json") -Depth 10
Write-Json -Value $summary -Path (Join-Path $ReportRoot "storage_summary.json") -Depth 8

$summaryLines = @(
    "# Storage Lifecycle Summary",
    "",
    "Generated: $($now.ToString("o"))",
    "",
    "- Dry run: $([bool]$DryRun)",
    "- Files audited: $($summary.total_files_audited)",
    "- Space used before: $($summary.space_used_before_human)",
    "- Space used after: $($summary.space_used_after_human)",
    "- Space moved/recovered from audited roots: $($summary.space_moved_or_recovered_human)",
    "- Files moved: $($summary.moved_files)",
    "- Archived files moved: $($summary.archive_count)",
    "- Safe-to-delete files moved to quarantine trash: $($summary.safe_to_delete_count)",
    "- Kept files: $($summary.kept_count)",
    "- Needs review: $($summary.needs_review_count)",
    "- Duplicate groups detected: $($summary.duplicate_groups)",
    "- Errors: $($summary.errors_count)",
    "",
    "## Destinations",
    "",
    "- Trash quarantine: $TrashRoot",
    "- Archive: $ArchiveRoot",
    "- AIpinho quarantine: $AipinhoQuarantineRoot",
    "",
    "## Safety",
    "",
    "No delete operation is used by this lifecycle script. Every moved file is recorded in storage_manifest.json for future restoration."
)
$summaryLines | Set-Content -LiteralPath (Join-Path $ReportRoot "storage_summary.md") -Encoding UTF8

$inventoryLines = @(
    "# Storage Inventory",
    "",
    "Full machine-readable inventory: storage_inventory.json.",
    "",
    "This markdown lists the largest 500 audited files for quick review.",
    "",
    "| Classification | Size | Age days | Reason | Path | Destination |",
    "|---|---:|---:|---|---|---|"
)
foreach ($item in ($inventory | Sort-Object -Property size -Descending | Select-Object -First 500)) {
    $dest = if ($item.new_path) { $item.new_path } else { "" }
    $inventoryLines += "| $($item.classification) | $(Format-Bytes $item.size) | $($item.age_days) | $($item.reason) | $($item.path) | $dest |"
}
$inventoryLines | Set-Content -LiteralPath (Join-Path $ReportRoot "storage_inventory.md") -Encoding UTF8

$dupeLines = @(
    "# Storage Duplicates",
    "",
    "Machine-readable duplicate groups are in storage_duplicates.json.",
    "",
    "| Hash | Size | Count | Files |",
    "|---|---:|---:|---|"
)
foreach ($group in ($duplicateGroups | Sort-Object -Property size -Descending | Select-Object -First 200)) {
    $files = ($group.files -join "<br>")
    $dupeLines += "| $($group.hash) | $(Format-Bytes $group.size) | $($group.count) | $files |"
}
$dupeLines | Set-Content -LiteralPath (Join-Path $ReportRoot "storage_duplicates.md") -Encoding UTF8

Write-MarkdownList -Path (Join-Path $ReportRoot "storage_keep.md") -Title "Storage KEEP" -Items ($keepItems | Sort-Object -Property size -Descending | Select-Object -First 1000)
Write-MarkdownList -Path (Join-Path $ReportRoot "storage_archive.md") -Title "Storage ARCHIVE" -Items ($archiveItems | Sort-Object -Property size -Descending)
Write-MarkdownList -Path (Join-Path $ReportRoot "storage_safe_to_delete.md") -Title "Storage SAFE_TO_DELETE" -Items ($safeItems | Sort-Object -Property size -Descending)
Write-MarkdownList -Path (Join-Path $ReportRoot "storage_needs_review.md") -Title "Storage NEEDS_REVIEW" -Items ($reviewItems | Sort-Object -Property size -Descending)

Write-Json -Value ([ordered]@{ summary = $summary; manifest_path = (Join-Path $ReportRoot "storage_manifest.json"); report_root = $ReportRoot }) -Path (Join-Path $ReportRoot "storage_run_result.json") -Depth 8

$summary | ConvertTo-Json -Depth 8
