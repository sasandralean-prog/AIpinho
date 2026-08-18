# AIpinho RC3 Known Issues

## KI-RC3-001 - Separate Artifact Port May Be Offline

The core backend serves artifact endpoints. Port 9098 can remain offline when the separated artifact service is not launched. This is a warning if token-protected artifact download through 9088 works.

## KI-RC3-002 - Full Visual Field Trial Still Recommended

Sprint 20 dogfood validated backend/kernel behavior. RC3 packaging should still be followed by a full mobile and launcher user-flow trial.

## KI-RC3-003 - Restore Is Preview-Only

Backup is available, but restore intentionally lists planned changes and does not overwrite state automatically.

