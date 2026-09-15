# Runtime Consolidation ? FireTest 5 Revalidation (2026-09-15)

- Campaign: `firetest5_runtime_consolidation_20260915T152207Z`
- Baseline SHA: `88885796255c1597c5e3658b393101d86be1f112`
- Result: PASS for runtime consolidation gates

## Phase matrix

| Phase | Run | Result | RuntimeTruth | PhaseOutcome | Role step | Events | Seq gaps/dups |
|---|---|---|---|---|---|---:|---|
| phase_1 | `task_run_5ffbb2400fe44a48bdf5650bda0f3146` | partial | partial | satisfied_with_limitations | completed | 330 | 0/0 |
| phase_2 | `task_run_adfaae43f020407983b0aab22663d94b` | completed | completed | satisfied | completed | 112 | 0/0 |
| phase_3 | `task_run_3747214532024e1cb444026c1d6d30b4` | completed | completed | satisfied | completed | 146 | 0/0 |
| phase_4 | `task_run_344afe5b85ff4c85b86de701b59f4915` | completed | completed | satisfied | completed | 147 | 0/0 |
| phase_5 | `task_run_d7821cc97b4349ecb4e0f02b74e106b3` | completed | completed | satisfied | completed | 115 | 0/0 |
| phase_6 | `task_run_a6dc9481ba6043c18e62746e9edfd825` | completed | completed | satisfied | completed | 149 | 0/0 |

## Confirmed fixes

- RuntimeTimeline event allocation stayed contiguous and unique in all six phases; the old Phase 4/6 collisions and gap did not recur.
- RuntimeTruth/PhaseOutcome no longer produces the old Phase 4 contradiction. Phases 2?6 completed with RuntimeTruth `completed`; Phase 1 remained `partial` and projected `satisfied_with_limitations` only through explicit governed use-safety.
- Phase 2 admitted Phase 1 evidence only after `safe_for_downstream_static_analysis=true_with_limitations` was evaluated as `COMPATIBLE_WITH_CONSTRAINT`; missing/false safety remains fail-closed.
- The planned `run_role_pipeline` step executed in every TaskRun. Persisted role runs used `readonly_project_report` with `supervisor_consistency` completed deterministically (`real_inference=false`).
- Runtime Doctor completed for all phases; observed latency was ~0.4?1.2 s, including the former problem phases 4 and 6.

## Integrity

- Workspace files: 1458 -> 1458; changed: 0.
- Workspace bytes: 544339738 -> 544339738.
- Corpus files: 166 -> 166; changed: 0.
- Corpus bytes: 287473867 -> 287473867.
- Repository HEAD unchanged during campaign: True.

## Authority distinction

- `RuntimeTruth=blocked/contradictory` is authoritative and forces the PhaseOutcome dependency status to `blocked`.
- `RuntimeTruth=partial` is not a success claim. It may expose limited evidence as `satisfied_with_limitations` only when the frozen downstream demand and explicit producer use-safety are compatible.
- `CanonicalOperationState=BLOCKED` for the partial Phase 1 means the operation cannot be represented as successful; it does not create a second semantic authority over edge-local limited-use admission.

## Known out-of-scope issue

- The existing Windows subprocess cp1252 decode error during media probing was observed again. Per scope, it was not fixed in this consolidation wave.

## Final regression after reboot

- The PC rebooted after the FireTest campaign and before the final consolidated regression completed.
- Filesystem state, branch changes, final validation reports, and quarantined raw FireTest evidence were verified intact after reboot.
- The final consolidated regression was rerun from scratch after reboot: `174 passed, 0 failed` in 279.10 s.
- `python -m compileall -q src`: PASS.
- FireTest machine manifest JSON parse: PASS.
- `git diff --check`: PASS after removing one trailing blank line in a test file.
- The repository-wide legacy test suite still contains failures reproducible on baseline `88885796255c1597c5e3658b393101d86be1f112`; those baseline failures were not reclassified as consolidation regressions.
