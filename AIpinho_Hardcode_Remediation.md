# AIpinho - Hardcode Remediation

Status: HARDCODE_REMEDIATION_PLAN_STARTED

## Classes

| Class | Meaning | Replacement |
|---|---|---|
| HARDCODE_PATH | Local/absolute paths | WorkspaceContext, config, path resolver |
| HARDCODE_RUNTIME | Ports, PIDs, runtime dirs | Runtime config, ProcessRuntimeState |
| HARDCODE_POLICY | allowed/ask/denied literals scattered | EffectivePolicyDecision enums |
| HARDCODE_CONFIG | Duplicated config defaults | Config registry |
| HARDCODE_DEBUG | debug/test switches in runtime | feature flags |
| HARDCODE_TEST | paths/providers in tests | fixtures and parametrization |
| HARDCODE_SECURITY | tokens/secrets/security defaults | secret provider and redaction |
| HARDCODE_TEMP | temp/cache paths | lifecycle/temp provider |

## Priority

1. Security and env: `.env.local`, tokens, provider keys.
2. Policy and runtime behavior: permission/status/action strings.
3. Paths and ports: workspace, runtime, backend, mobile, Tailscale/firewall.
4. Provider/model hardcodes: Gemini/Codex/OpenAI/Llama as capabilities, not branches.
5. Test hardcodes: fixtures, parametrized environments.

## Rule

Hardcode removal must not reduce determinism. Replace hardcodes with explicit config, contracts, registries, factories, providers, or policy tables.

## Wave 2 Remediation

- Hardened `HARDCODE_POLICY` vocabulary handling: unknown policy statuses no longer fall through to `allowed`.
- `expired` and `stale` policy states now map to explicit block reason codes.
- Remaining raw policy string comparisons are listed in the final compatibility backlog and should be replaced by `CanonicalPermission` adaptation through `EffectivePolicyDecisionService`.

## Wave 3 Remediation

- Hardened `HARDCODE_RUNTIME` identity assumptions: executable `TaskRun` records must carry canonical `task_id`, `task_run_id`, `operation_id`, and matching bootstrap context.
- Replaced one runtime approval binding that wrote `task_id=run_id` with canonical `task_id=run.task_id`.
- UI status fallback now uses canonical `unknown` instead of invalid literal `none`.
- Remaining `run_id` as `task_id` compatibility fallbacks are tracked for final migration.

## Wave 4 Remediation

- Hardened `HARDCODE_RUNTIME` observability assumptions: execution now requires initial timeline event types instead of relying on `TaskRun.status` alone.
- The initial timeline event contract is explicit and deterministic: `run_created` plus `task_bootstrap_created`.
- Remaining event type duplication across non-TaskRun domains is tracked as compatibility debt.

## Wave 5 Remediation

- Hardened `HARDCODE_RUNTIME` artifact identity assumptions: governed artifacts can no longer be created through `ArtifactRuntimeService` without a producer step and task/task-run binding.
- Hardened artifact evidence validation: missing `task_id`, `task_run_id`, or `event_id` now blocks artifact use as authoritative evidence.
- Runtime Doctor report artifacts now declare their diagnostic binding source in metadata when no observed TaskRun exists.
- Remaining artifact `run_id`-as-`task_id` compatibility and direct registry access are tracked for the final compatibility wave.

## Wave 6 Remediation

- Hardened `HARDCODE_RUNTIME` success assumptions: `TaskRunResult.status == completed` no longer makes canonical operation state `COMPLETED` without RuntimeTruth evidence.
- Hardened artifact truth handling: completed results with orphan artifacts now produce blocked runtime truth.
- Universal Task Session safe-success fields now mirror canonical operation state instead of duplicating completion booleans locally.
- Remaining local `final_answer` and status summaries are tracked as compatibility debt until they are gated by RuntimeTruth.

## Wave 7 Remediation

- Replaced the configured context plan store path `data/runtime/context_plans` with canonical `data/runtime/context/plans`.
- Updated the `ContextUsageAuditService` fallback path to the same canonical location.
- Moved existing context plan data physically instead of adding a repository facade.
- Archived empty legacy runtime directories under `data/runtime/repository_legacy/empty_dirs` instead of deleting them.

## Wave 7.5 Remediation

- Replaced local chat citation-bypass string checks with config-driven `ContextPromptPolicyService`.
- Added context prompt policy configuration for citation/source bypass and automatic context activation under `config/context/context_prompt_injection_policy.yaml`.
- Removed the obsolete chat router shim instead of keeping a hidden import fallback.
- Replaced several `task_id = run_id` runtime assumptions with distinct canonical `task_id` plus `task_run_id`/`result_ref_id`.
- Preserved legacy lookup aliases where needed, but stopped writing new approval/runtime records with task-run IDs in the task identity field.

## Wave 10 Updates

- Removed stale `chat_router` module hint from Patch Intelligence seed knowledge and replaced it with canonical semantic/governance/runtime module names.
- Closed test helper hardcode/duplication path by migrating direct helper imports from `conftest.py` to `tests/support/runtime_fixtures.py`.
- Hardened identity metadata in Speaker/chat publication paths by carrying `task_id` and `task_run_id` separately in internal payloads.
- Removed generated `__pycache__` directories from the project root after validation runs.

## Wave 8 Remediation

- Removed an implicit `artifact_request -> write_files` assumption for Artifact Store outputs that do not mutate a workspace.
- Final-answer recall now uses stored `result_ref_id` records instead of text reconstruction.
- Persistent chat route now generates and stores stable `result_ref_id` values before metadata persistence.
- No `ALMOST_DONE`, `PROCESSING`, `Generating`, or fake progress markers were found in `apps` or `src` during Wave 8 verification.
