# RC2 Regression Matrix

## Write Flow

- simple create-file prompt routes to `governed_file_write`;
- target_mutable create_file succeeds through Tool Gateway;
- source_readonly write is blocked;
- missing workspace returns clarification;
- analysis + artifact request remains analysis/artifact, not workspace write.

## Runtime Hygiene

- stale active run is found by preview;
- apply marks stale run cancelled;
- no evidence deletion.

## Health

- `/api/v1/health` remains simple liveness;
- `/api/v1/health/semantics` separates backend, operational and observability states.

## QA Notes

- Mobile and Launcher all-tabs QA should confirm visual state matches these backend semantics.
