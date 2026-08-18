# Release Notes RC3

## Sprint 26

- Added governed local sandbox under `sandboxes/`.
- Added sandbox workspace/task/file/shell/artifact/cleanup APIs.
- Added Tool Gateway metadata and registered `sandbox_*` tools.
- Added mobile sandbox view-model and dashboard card.
- Added regression suite flag `--sandbox`.

Known follow-up: dedicated Launcher/Mobile interactive sandbox screens are not part of this backend-first sprint; current UI contract is available through the mobile view-model.
# Sprint 27 Addendum

- Added Sandbox Project Factory for governed project generation.
- Added Android Kotlin, Python and static web templates for sandbox deliverables.
- Added artifact status model and mobile download gating for ready/failed/blocked states.
- Added `project_factory` regression profile.
- Live smoke generated a token-protected `SapoAndando.zip` artifact and confirmed unauthorized downloads return `401`.
