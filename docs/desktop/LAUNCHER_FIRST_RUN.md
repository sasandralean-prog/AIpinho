# Launcher First Run

## Open

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\open_launcher.ps1
```

From the RC3 package:

```text
OPEN_LAUNCHER.bat
```

The script prefers `dist\AIpinhoLauncher.exe` when available. If not available, it opens the Python launcher entrypoint.

## Expected Screens

- Dashboard.
- Chat.
- Gemini.
- Lucio.
- Codex.
- Pipeline.
- Debugger 2.0.
- Config.

## Safety Checks

- Token must not be displayed.
- Artifact downloads must use token-protected backend endpoints.
- Backend offline errors should be human-readable.

