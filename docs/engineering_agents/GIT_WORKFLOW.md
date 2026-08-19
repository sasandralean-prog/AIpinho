# Engineering Git Workflow

## Task Start

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git switch -c agent/<agent>/<task>
```

Begin work only after local `main` and `origin/main` match for tracked files.

## Task Execution

- Work only on the task branch.
- Keep commits logical and bounded.
- Do not include unrelated drive-by changes.
- Do not stage secrets, runtime state, GGUF/model files, corpora, caches, or
  raw heavy evidence.

## Main Advanced

Before final validation:

```powershell
git fetch origin
```

If `origin/main` advanced, merge it into the task branch:

```powershell
git merge origin/main
```

Resolve conflicts consciously and rerun affected validation. Do not silently
rebase published work by default.

## Hybrid Handoff

For hybrid/cloud-to-local work:

```text
push task branch
same branch fetched locally
local validation
additional commits on same branch if needed
```

The branch carries the task. Do not recreate the implementation in a second
branch merely because the environment changed.

## Canonization

When the task branch is fully validated:

```powershell
git push -u origin agent/<agent>/<task>
git switch main
git pull --ff-only origin main
git merge --no-ff agent/<agent>/<task>
```

Use a meaningful merge commit message, run final appropriate validation, then:

```powershell
git push origin main
```

## Local Sync

After pushing main:

```powershell
git switch main
git fetch origin
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Required invariant:

```text
TRACKED_SYNCHRONIZATION_INVARIANT:
tracked(local main) == tracked(origin/main)
```

## Forbidden

- force push as a convenience;
- destructive reset;
- `git clean` to reconcile local state;
- broad restore/checkout of local work;
- deleting ignored or untracked local overlay resources.
