[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:9088"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportDir = Join-Path $root "reports\health"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Invoke-OptionalJson {
    param([string]$Name, [string]$Uri, [string]$Method = "GET")
    try {
        $response = Invoke-RestMethod -Uri $Uri -Method $Method -TimeoutSec 12
        [pscustomobject]@{ name = $Name; ok = $true; data = $response; error = $null }
    } catch {
        [pscustomobject]@{ name = $Name; ok = $false; data = $null; error = $_.Exception.Message }
    }
}

$statusJson = & (Join-Path $root "scripts\status_aipinho.ps1") -BaseUrl $BaseUrl -Json | ConvertFrom-Json
$statusReport = & (Join-Path $root "scripts\status_aipinho.ps1") -BaseUrl $BaseUrl -WriteReport

$checks = @(
    Invoke-OptionalJson -Name "health_semantics" -Uri "$BaseUrl/api/v1/health/semantics"
    Invoke-OptionalJson -Name "agents_status" -Uri "$BaseUrl/api/v1/agents/status"
    Invoke-OptionalJson -Name "project_profiles_status" -Uri "$BaseUrl/api/v1/projects/profiles/status"
    Invoke-OptionalJson -Name "project_profiles_health" -Uri "$BaseUrl/api/v1/projects/profiles/doctor/health"
    Invoke-OptionalJson -Name "mobile_project_profiles" -Uri "$BaseUrl/api/v1/mobile/view-model/projects"
    Invoke-OptionalJson -Name "mobile_dashboard" -Uri "$BaseUrl/api/v1/mobile/view-model/dashboard"
    Invoke-OptionalJson -Name "mobile_debugger" -Uri "$BaseUrl/api/v1/mobile/view-model/debugger"
    Invoke-OptionalJson -Name "runtime_hygiene_preview" -Method "POST" -Uri "$BaseUrl/api/v1/runtime/hygiene/preview?max_age_hours=24&limit=20&kinds=run,session,delegation"
)

$apkPath = Join-Path $root "apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk"
$launcherExe = Join-Path $root "dist\AIpinhoLauncher.exe"
$launcherScript = Join-Path $root "scripts\open_launcher.ps1"
$criticalDocs = @(
    "docs\operations\OPERATIONAL_RUNBOOK.md",
    "docs\operations\CONFIGURATION_GUIDE.md",
    "docs\mobile\MOBILE_PAIRING_GUIDE.md",
    "docs\desktop\LAUNCHER_FIRST_RUN.md"
)

$docStatus = foreach ($path in $criticalDocs) {
    [pscustomobject]@{ path = $path; exists = Test-Path -LiteralPath (Join-Path $root $path) }
}

$warnings = [System.Collections.Generic.List[string]]::new()
if ($statusJson.status -ne "ready") { $warnings.Add("status_aipinho returned $($statusJson.status)") }
if (-not (Test-Path -LiteralPath $apkPath)) { $warnings.Add("mobile APK not found") }
if (-not (Test-Path -LiteralPath $launcherExe) -and -not (Test-Path -LiteralPath $launcherScript)) { $warnings.Add("launcher entrypoint not found") }
foreach ($doc in $docStatus) {
    if (-not $doc.exists) { $warnings.Add("missing doc: $($doc.path)") }
}
foreach ($check in $checks) {
    if (-not $check.ok) { $warnings.Add("$($check.name) failed: $($check.error)") }
}

$verdict = if ($statusJson.status -eq "ready" -and $warnings.Count -eq 0) {
    "ready_for_local_daily_use"
} elseif ($statusJson.status -in @("ready", "ready_with_warnings")) {
    "ready_with_warnings"
} else {
    "requires_patch"
}

$doctor = [pscustomobject]@{
    status = $verdict
    generated_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    status_check = $statusJson
    checks = $checks
    mobile_apk = [pscustomobject]@{ path = $apkPath; exists = Test-Path -LiteralPath $apkPath }
    launcher = [pscustomobject]@{
        exe_path = $launcherExe
        exe_exists = Test-Path -LiteralPath $launcherExe
        script_path = $launcherScript
        script_exists = Test-Path -LiteralPath $launcherScript
    }
    docs = $docStatus
    cleanup_preview_note = "Runtime cleanup preview is diagnostic only. This doctor does not apply cleanup."
    warnings = @($warnings)
}

$jsonPath = Join-Path $reportDir "doctor_aipinho_$stamp.json"
$mdPath = Join-Path $reportDir "doctor_aipinho_$stamp.md"
[System.IO.File]::WriteAllText($jsonPath, ($doctor | ConvertTo-Json -Depth 20), $Utf8NoBom)
@(
    "# AIpinho Doctor $stamp",
    "",
    "Verdict: $verdict",
    "",
    "## Human Summary",
    "",
    $(if ($verdict -eq "ready_for_local_daily_use") { "AIpinho esta pronta para uso local assistido." } elseif ($verdict -eq "ready_with_warnings") { "AIpinho esta online, mas ha warnings documentados." } else { "AIpinho nao esta pronta sem correcao." }),
    "",
    "## Warnings",
    ""
) + ($(if ($warnings.Count) { $warnings | ForEach-Object { "- $_" } } else { "- none" })) + @(
    "",
    "## Generated Files",
    "",
    "- $jsonPath",
    "- $mdPath"
) | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Output "AIpinho doctor verdict: $verdict"
if ($warnings.Count) {
    Write-Output "Warnings:"
    $warnings | ForEach-Object { Write-Output "- $_" }
}
Write-Output "Reports:"
Write-Output $mdPath
Write-Output $jsonPath
