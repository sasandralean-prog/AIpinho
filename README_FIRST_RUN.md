# AIpinho RC3 - First Run

Use these commands from `C:\Dev\AIpinho`.

## Start

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_aipinho.ps1
```

## Check Status

```powershell
powershell -ExecutionPolicy Bypass -File scripts\status_aipinho.ps1 -WriteReport
```

## Run Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor_aipinho.ps1
```

## Open Launcher

```powershell
powershell -ExecutionPolicy Bypass -File scripts\open_launcher.ps1
```

## Mobile Pairing Help

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prepare_mobile_pairing.ps1
```

## Stop

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop_aipinho.ps1
```

## Safety Notes

- Provider keys and tokens must stay outside frontend bundles and reports.
- Downloads use artifact ids and Authorization headers.
- Port 9099 is a monitor/supervisor control plane and must not restart itself.
- Backup is sanitized by default.
- Restore is preview-only in RC3.

