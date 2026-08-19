---
name: aipinho-git-wave
description: Use for canonical AIpinho engineering Git lifecycle, branch ownership, safe handoff, merge, push, and final local sync.
---

# AIpinho Git Wave

## Lifecycle

1. Classify the execution environment and proof authority.
2. Synchronize `main`.
3. Create `agent/<agent>/<task>` from synchronized `main`.
4. Implement on the task branch.
5. Validate the allowed scope.
6. Decide whether local validation is required.
7. Handoff the same branch if hybrid/local proof is needed elsewhere.
8. Update canonical reports/docs.
9. Fetch latest `origin/main`.
10. Merge `origin/main` into the task branch if main advanced.
11. Rerun affected validation.
12. Push the task branch.
13. Merge validated task branch into `main`.
14. Push `main`.
15. Synchronize local `main`.
16. Prove the tracked synchronization invariant.

## Forbidden

- force push as a convenience;
- `git reset --hard`;
- `git clean` as cleanup;
- broad restore/checkout of local work;
- development directly on `main`;
- hiding merge conflicts;
- deleting local overlay resources.

## Invariants

```text
TRACKED_SYNCHRONIZATION_INVARIANT:
tracked(local main) == tracked(origin/main)

LOCAL_OVERLAY_INVARIANT:
ignored/untracked local execution resources remain local and preserved
```
