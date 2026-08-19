# Local Execution Overlay

AIpinho on Rafa's PC is:

```text
Repository Truth + Local Execution Overlay
```

## Repository Truth

Repository truth consists of tracked files, Git history, and `origin/main`.

## Local Execution Overlay

Local overlay may include:

```text
secrets
  .env*

models
  *.gguf

external runtimes/binaries
runtime state
local corpora/datasets
heavy generated artifacts
local FireTest environment
caches and temporary workspaces
```

These resources can be necessary for local validation, but they are not
repository truth and should not be committed.

## Local Overlay Invariant

```text
LOCAL_OVERLAY_INVARIANT:
ignored/untracked local execution resources remain local and preserved
```

Do not delete, normalize, stage, print, or upload local overlay resources just
to make GitHub and the PC directory byte-identical.

## Raw Evidence and Canonical Reports

```text
raw local evidence
-> bounded summary/digest/result
-> canonical report
-> Git
```

Raw evidence may be large, sensitive, noisy, or machine-specific. Canonical
reports should be bounded and safe to version.
