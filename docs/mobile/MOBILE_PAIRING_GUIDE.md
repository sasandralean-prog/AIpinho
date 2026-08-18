# Mobile Pairing Guide

## Connection Options

### ADB Reverse

Use when the phone is connected by USB:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prepare_mobile_pairing.ps1 -ApplyAdbReverse
```

Equivalent manual commands:

```text
adb reverse tcp:9088 tcp:9088
adb reverse tcp:9089 tcp:9089
adb reverse tcp:9098 tcp:9098
adb reverse tcp:9099 tcp:9099
```

### Wi-Fi LAN

Use the LAN URL printed by:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prepare_mobile_pairing.ps1
```

Test from the phone:

```text
http://<LAN-IP>:9088/api/v1/health
```

### Tailscale

Keep Tailscale enabled on PC and phone, then use the Tailscale URL printed by the pairing script.

## Token

The token is sent in the `Authorization` header. It must not appear in URLs, reports, raw logs or screenshots.

## APK

The RC3 package includes the debug APK when build artifacts are available:

`dist\aipinho_local_rc3\mobile\aipinho-mobile-rc3.apk`

## Artifact Downloads

Artifact buttons call backend download endpoints with a token header. The app should not open protected artifact URLs in an external browser.

## Troubleshooting

- Backend offline: run `STATUS_AIPINHO.bat`.
- Dashboard degraded: run `DOCTOR_AIPINHO.bat`.
- Token invalid: reset pairing and confirm the app stores the current token.
- Download fails: confirm backend is online and token is present.

