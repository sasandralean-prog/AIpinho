# RC2 Fix Plan

Date: 2026-06-13

## Verdict Driver

Sprint 16 validated the RC1 multi-agent kernel, LAN/Tailscale backend access, mobile dashboard visibility, artifact generation, and Lucio/Gemini delegation after localized hotfixes.

RC2 is required because the main AIpinho chat still does not route explicit safe file-write prompts into the governed create_file/write contract. The Tool Gateway and agent tabs can perform governed writes, but the primary chat path can still return a rebuild/workspace_missing block for a simpler create-file request.

## Required Fixes

1. Main chat write bridge
   - Add a general operation contract for explicit create_file/modify_file requests.
   - Preserve workspace registry, policy, preview/approval when required, validation, events and traces.
   - Do not hardcode filenames, prompts, project names or paths.

2. Runtime state hygiene
   - Add an official audited cleanup/retention command for stale sessions, runs, delegations and approvals.
   - Preserve debug bundles before cleanup.
   - Avoid dashboard degradation from historical field-trial residue.

3. Full visual QA
   - Run mobile all-tabs smoke on physical device or emulator.
   - Run launcher all-tabs smoke.
   - Capture screenshots and UI tree/log evidence where available.

4. 9099 control service clarity
   - Confirm whether monitor/control 9099 is meant to run continuously in this deployment.
   - Align mobile dashboard wording if 9099 status is derived from config rather than a live listener.

## Acceptance Criteria

- Main chat can create a file in a target_mutable workspace through governed execution.
- Source_readonly paths never receive writes.
- Dashboard starts clean after official cleanup and stays consistent after field trial.
- Mobile and launcher visual smoke evidence exists.
- Regression quick/all/security pass after fixes.
