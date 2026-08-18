# AIpinho RC3 Release Notes

## Focus

RC3 focuses on local daily-use readiness:

- start/stop/status scripts;
- operational doctor;
- mobile pairing guide;
- launcher first-run guide;
- backup and restore preview;
- release package under `dist\aipinho_local_rc3`;
- health and release reports.

## Safety

- No token in URL.
- No provider key in frontend, logs or reports.
- Restore is preview-only.
- Runtime cleanup is suggested through preview, not applied blindly.
- Port 9099 does not restart itself.

## Known Warnings

- Realtime 9089 and artifact port 9098 can be optional depending on the local deployment shape.
- Full mobile/launcher tap-by-tap RC3 field trial remains recommended after packaging.

