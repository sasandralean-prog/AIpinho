# Backup and Restore

## Backup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup_aipinho.ps1
```

Backup includes:

- docs;
- reports;
- generated artifacts;
- agent runtime metadata;
- hygiene previews;
- sanitized config copy.

Backup excludes:

- provider secrets;
- bearer tokens in clear text;
- raw unsanitized logs;
- cache directories.

## Restore Preview

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore_aipinho.ps1 -BackupZip <path>
```

RC3 restore is preview-only. It lists archive entries and writes a report under `reports\restore`.

## Restore Policy

Actual restore must have a dedicated plan before overwriting local state.

