[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Read-Secret([string]$Prompt) {
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$primary = Read-Secret "Gemini primary API key"
$secondary = Read-Secret "Gemini secondary API key (optional)"

if (-not $primary) {
    throw "Primary Gemini key is required."
}

[Environment]::SetEnvironmentVariable("GEMINI_API_KEY_PRIMARY", $primary, "User")
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY_SECONDARY", $secondary, "User")
[Environment]::SetEnvironmentVariable("GEMINI_EXECUTOR_ENABLED", "true", "User")
[Environment]::SetEnvironmentVariable("CODEX_AGENT_ENABLED", "true", "User")

Write-Output "Agent secrets configured in the Windows user environment."
Write-Output "No secret value was printed. Restart the AIpinho backend to apply."
