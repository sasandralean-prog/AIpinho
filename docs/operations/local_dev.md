# Local development

## Official ports

- API: `9088`
- Auxiliary channel reservation: `9089`

The API binds to `0.0.0.0` for localhost, private LAN, and Tailscale access. Port `9089` is reserved and has no listener until a dedicated auxiliary service is implemented.

## Start

```powershell
C:\Dev\AIpinho\scripts\dev\start_aipinho_9088.ps1
```

Optional local-only bind:

```powershell
C:\Dev\AIpinho\scripts\dev\start_aipinho_9088.ps1 -HostName 127.0.0.1
```

## Stop

```powershell
C:\Dev\AIpinho\scripts\dev\stop_aipinho_9088.ps1
```

The stop script refuses to terminate a process unless its command line contains `aipinho.main:app`.

## Firewall

Run once from an elevated PowerShell session:

```powershell
C:\Dev\AIpinho\scripts\dev\configure_aipinho_firewall_9088_9089.ps1
```

The script creates persistent inbound rules for:

- LAN on Private/Domain profiles, limited to `LocalSubnet`.
- Tailscale, limited to `100.64.0.0/10`.

It does not create an unrestricted Public rule.

## Smoke

```powershell
C:\Dev\AIpinho\scripts\validation\smoke_aipinho_9088_9089.ps1
```

The smoke script discovers current LAN and Tailscale addresses instead of storing machine-specific IPs.
