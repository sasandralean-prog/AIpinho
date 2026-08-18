# G18 - Legacy Deletion Preflight

Status: G18_LEGACY_DELETION_PREFLIGHT_READY

Generated UTC: 2026-06-26T10:32:19.629848+00:00

## Delete decisions

- `config/runtime/runtime_profiles.yaml`: `delete_ready` and deleted in G19.
- `chat_router.py`: `keep_archived_for_now`.
- `continue_integration_router.py`: `keep_archived_for_now`.

Reason: routers are not imported by active runtime, but remain large rollback artifacts with historical/test references. Deleting them permanently is safe later after broader full-suite cleanup.

Manifest: `reports/governance_block_c/G18_legacy_deletion_manifest.json`.
