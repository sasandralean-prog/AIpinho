# AIpinho Troubleshooting

## Backend Offline

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\status_aipinho.ps1
```

If 9088 is offline:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_aipinho.ps1
```

## Port 9088 Occupied

The start script refuses to replace unrelated processes. Identify the owner before stopping anything.

## Artifact Download 401

- Confirm the app sends `Authorization: Bearer <token>`.
- Confirm the URL does not contain token values.
- Confirm the artifact id exists.

## Mobile Does Not Connect

- Use ADB reverse for USB.
- Use LAN or Tailscale URL for wireless.
- Confirm `/api/v1/health` works from the phone network.

## Dashboard Degraded

Use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\doctor_aipinho.ps1
```

Degraded observability can mean stale runtime evidence, not backend outage.

## Runtime State Stale

Use runtime hygiene preview only:

```text
POST /api/v1/runtime/hygiene/preview
```

Do not apply cleanup blindly.

## Validation Failed

Read the validation evidence. A failed validation must not be marked completed.

