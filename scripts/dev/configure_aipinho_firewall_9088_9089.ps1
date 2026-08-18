[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$BootstrapPort = 9080,
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 9088,
    [ValidateRange(1, 65535)]
    [int]$AuxiliaryPort = 9089,
    [ValidateRange(1, 65535)]
    [int]$ArtifactPort = 9098,
    [ValidateRange(1, 65535)]
    [int]$MonitorPort = 9099
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell session."
}

$services = @(
    @{ Label = "Bootstrap"; Port = $BootstrapPort },
    @{ Label = "API"; Port = $ApiPort },
    @{ Label = "Auxiliary"; Port = $AuxiliaryPort },
    @{ Label = "Artifact"; Port = $ArtifactPort },
    @{ Label = "Monitor"; Port = $MonitorPort }
)
$definitions = @()
foreach ($service in $services) {
    $definitions += @{ Name = "AIpinho $($service.Label) $($service.Port) LAN"; Port = $service.Port; Profile = "Private,Domain"; Remote = "LocalSubnet" }
    $definitions += @{ Name = "AIpinho $($service.Label) $($service.Port) Tailscale"; Port = $service.Port; Profile = "Any"; Remote = "100.64.0.0/10" }
}

foreach ($definition in $definitions) {
    $existing = Get-NetFirewallRule -DisplayName $definition.Name -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Remove-NetFirewallRule
    }
    New-NetFirewallRule `
        -DisplayName $definition.Name `
        -Description "Persistent inbound rule for AIpinho. Public internet is not allowed." `
        -Direction Inbound `
        -Action Allow `
        -Enabled True `
        -Profile $definition.Profile `
        -Protocol TCP `
        -LocalPort $definition.Port `
        -RemoteAddress $definition.Remote `
        -EdgeTraversalPolicy Block `
        -PolicyStore PersistentStore | Out-Null
    Write-Output "Configured: $($definition.Name) remote=$($definition.Remote) profile=$($definition.Profile)"
}

Write-Output "AIpinho firewall configuration complete. No unrestricted Public rule was created."
