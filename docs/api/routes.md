# API Routes

AIpinho exposes versioned API routes under `/api/v1`.

## Foundation

- `GET /api/v1/health`
- `GET /api/v1/status`
- `GET /api/v1/config/status`
- `GET /api/v1/routes`

## Chat And Prompt Intelligence

- `POST /api/v1/chat`
- `POST /api/v1/chat/preview`
- `GET /api/v1/chat/status`
- `POST /api/v1/intent/analyze`
- `POST /api/v1/intent/contract-preview`

## Policy

- `GET /api/v1/policy/status`
- `GET /api/v1/policy/actions`
- `GET /api/v1/policy/precedence`
- `GET /api/v1/policy/capabilities`
- `GET /api/v1/policy/approvals`
- `POST /api/v1/policy/resolve`
- `POST /api/v1/policy/explain`
- `POST /api/v1/policy/contract-preview`

## Sessions And Drafts

- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/sessions/{session_id}/events`
- `DELETE /api/v1/sessions/{session_id}`
- `POST /api/v1/task-drafts`
- `GET /api/v1/task-drafts/{draft_id}`
- `GET /api/v1/task-drafts/{draft_id}/events`
- `POST /api/v1/task-drafts/{draft_id}/refresh-policy`
- `DELETE /api/v1/task-drafts/{draft_id}`

## Preview And Approval Lifecycle

- `POST /api/v1/previews`
- `POST /api/v1/previews/from-draft/{draft_id}`
- `GET /api/v1/previews/{preview_id}`
- `GET /api/v1/previews/{preview_id}/events`
- `POST /api/v1/previews/{preview_id}/refresh-policy`
- `POST /api/v1/approvals`
- `GET /api/v1/approvals/{approval_id}`
- `GET /api/v1/approvals/{approval_id}/events`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`
- `POST /api/v1/approvals/{approval_id}/cancel`
- `POST /api/v1/approvals/{approval_id}/refresh-policy`

Approval decisions are non-executing records in Sprint 05. They mark `approved_for_future_execution`, `rejected`, or `cancelled` states without running tools or applying patches.

## Tools And Dry-Run

- `GET /api/v1/tools`
- `GET /api/v1/tools/{tool_id}`
- `GET /api/v1/tools/status`
- `POST /api/v1/tools/validate`
- `POST /api/v1/tools/preview`
- `POST /api/v1/tools/dry-run`
- `POST /api/v1/tools/dry-run/from-preview/{preview_id}`
- `POST /api/v1/tools/dry-run/from-draft/{draft_id}`

Tool dry-runs are simulations only and still never execute side effects.

## Read-Only Tool Execution

- `GET /api/v1/tools/execution-status`
- `POST /api/v1/tools/execute-readonly`
- `POST /api/v1/tools/execute-readonly/from-preview/{preview_id}`
- `POST /api/v1/tools/execute-readonly/from-draft/{draft_id}`
- `GET /api/v1/tools/executions/{execution_id}`
- `GET /api/v1/tools/executions/{execution_id}/events`

Sprint 07 enables real execution only for explicit read-only filesystem tools inside allowed workspaces. Writes, shell, patch apply, git write, memory write, RAG mutation, network and LLM calls remain disabled. Every allowed or blocked read-only execution produces an audit event without logging file content.

## Read-Only Task Runtime

- `GET /api/v1/task-runtime/status`
- `POST /api/v1/task-runs`
- `POST /api/v1/task-runs/from-draft/{draft_id}`
- `POST /api/v1/task-runs/from-preview/{preview_id}`
- `POST /api/v1/task-runs/{run_id}/start`
- `POST /api/v1/task-runs/{run_id}/cancel`
- `GET /api/v1/task-runs/{run_id}`
- `GET /api/v1/task-runs/{run_id}/events`
- `GET /api/v1/task-runs/{run_id}/trace`
- `GET /api/v1/task-runs/{run_id}/result`
- `GET /api/v1/task-runs`

Sprint 16 TaskRuns are supervised and read-only. Creation never starts execution. Chat may suggest or inspect TaskRuns, but cannot auto-start them. Results are safe-to-display summaries with raw content omitted by the runtime store.

## Validation And Report Quality Gates

- `GET /api/v1/validation/status`
- `POST /api/v1/validation/task-run/{run_id}`
- `POST /api/v1/validation/task-result`
- `POST /api/v1/validation/report`
- `POST /api/v1/validation/report/{report_id}`
- `POST /api/v1/validation/role-pipeline/{run_id}`
- `POST /api/v1/validation/side-effects`
- `POST /api/v1/validation/evidence`
- `POST /api/v1/validation`
- `GET /api/v1/validation/results/{validation_id}`
- `GET /api/v1/validation/results/{validation_id}/trace`

Sprint 17 adds deterministic validation gates for task run results, project reports, role pipeline outputs, evidence quality and side-effect signals. Validation stores only sanitized audit metadata under runtime validation storage; it does not execute tools, repair outputs, mutate workspaces, call models, write memory or ingest RAG.

## Artifact Writer Preview

- `GET /api/v1/artifacts/status`
- `POST /api/v1/artifacts/drafts`
- `GET /api/v1/artifacts/drafts/{draft_id}`
- `POST /api/v1/artifacts/previews`
- `POST /api/v1/artifacts/previews/from-report/{report_id}`
- `POST /api/v1/artifacts/previews/from-task-run/{run_id}`
- `POST /api/v1/artifacts/previews/{preview_id}/refresh-validation`
- `POST /api/v1/artifacts/previews/{preview_id}/request-approval`
- `GET /api/v1/artifacts/previews/{preview_id}`
- `GET /api/v1/artifacts/previews/{preview_id}/diff`
- `GET /api/v1/artifacts/previews/{preview_id}/trace`
- `GET /api/v1/artifacts/previews`

Sprint 18 adds preview-only controlled file output. Artifact previews validate target path, content, format, risk and approval requirement, but never write files, create directories, overwrite targets, apply patches, run shell/git, mutate RAG or write memory.

## Artifact Write Execution

- `GET /api/v1/artifacts/write/status`
- `POST /api/v1/artifacts/write/from-preview/{preview_id}`
- `POST /api/v1/artifacts/write/{write_run_id}/execute`
- `POST /api/v1/artifacts/write/{write_run_id}/cancel`
- `GET /api/v1/artifacts/write/runs/{write_run_id}`
- `GET /api/v1/artifacts/write/runs/{write_run_id}/events`
- `GET /api/v1/artifacts/write/runs/{write_run_id}/trace`
- `GET /api/v1/artifacts/write/runs/{write_run_id}/result`
- `GET /api/v1/artifacts/write/runs`

Sprint 19 enables approved non-code artifact writes only. A write requires an approved `ArtifactPreview`, a valid approval, target revalidation, content hash lock, target lock, explicit execute endpoint, atomic text write and post-write validation. Direct payload writes, source code writes, active config writes, scripts, patch, shell, git write, RAG/vectorstore mutation, memory write and model tool-calling remain disabled.

## Patch Planning

- `GET /api/v1/patch-plans/status`
- `POST /api/v1/patch-plans`
- `POST /api/v1/patch-plans/from-report/{report_id}`
- `POST /api/v1/patch-plans/from-task-run/{run_id}`
- `POST /api/v1/patch-plans/from-validation/{validation_id}`
- `POST /api/v1/patch-plans/{plan_id}/refresh`
- `POST /api/v1/patch-plans/{plan_id}/validate`
- `GET /api/v1/patch-plans/{plan_id}`
- `GET /api/v1/patch-plans/{plan_id}/diff`
- `GET /api/v1/patch-plans/{plan_id}/evidence`
- `GET /api/v1/patch-plans/{plan_id}/risk`
- `GET /api/v1/patch-plans/{plan_id}/quality`
- `GET /api/v1/patch-plans/{plan_id}/trace`
- `GET /api/v1/patch-plans`

Sprint 20 adds proposal-only patch planning and diff preview. Patch plans can map affected files, link evidence, read targets read-only, generate unified diff previews, calculate risk, create rollback notes and suggest tests. There is no apply endpoint, no workspace write, no shell/git, no test execution and no model tool-calling authority.

## Patch Quality Gate

- `GET /api/v1/patch-quality/status`
- `POST /api/v1/patch-quality/validate-plan/{plan_id}`
- `POST /api/v1/patch-quality/validate-diff`
- `POST /api/v1/patch-quality/validate-static`
- `POST /api/v1/patch-quality/validate-plan/{plan_id}/refresh`
- `GET /api/v1/patch-quality/results/{quality_id}`
- `GET /api/v1/patch-quality/results/{quality_id}/trace`
- `GET /api/v1/patch-quality/results`

Sprint 21 adds deterministic static quality validation for patch plans and diff proposals. The gate parses unified diffs, validates hunk/snapshot consistency, checks static syntax, detects hardcode, policy bypass and security regression signals, validates rollback/test evidence and stores an auditable result. `passed` means eligible for future apply review only; apply, write, shell, git and test execution remain disabled.

## Patch Apply

- `GET /api/v1/patch-apply/status`
- `POST /api/v1/patch-apply/request-approval/{plan_id}`
- `POST /api/v1/patch-apply/runs/from-plan/{plan_id}`
- `POST /api/v1/patch-apply/runs/{apply_run_id}/execute`
- `POST /api/v1/patch-apply/runs/{apply_run_id}/cancel`
- `POST /api/v1/patch-apply/runs/{apply_run_id}/rollback`
- `GET /api/v1/patch-apply/runs/{apply_run_id}`
- `GET /api/v1/patch-apply/runs/{apply_run_id}/events`
- `GET /api/v1/patch-apply/runs/{apply_run_id}/trace`
- `GET /api/v1/patch-apply/runs/{apply_run_id}/result`
- `GET /api/v1/patch-apply/runs`
- `GET /api/v1/patch-plans/{plan_id}/apply-status`

Sprint 22 adds the first controlled patch mutation flow. Patch apply requires an existing PatchPlan, DiffProposal, `passed` Patch Quality Gate, explicit `patch_apply` approval, operator confirmation, snapshot/diff/target locks, internal backup, atomic write and post-apply validation. Approval alone does not apply. Creating a run does not apply. Chat does not apply. Shell, git, direct diff apply, payload patch apply, new/delete/rename, binary files, forbidden roots and test execution remain disabled.

## Engineering Memory Candidates

- `GET /api/v1/memory/status`
- `GET /api/v1/memory/candidates/status`
- `POST /api/v1/memory/candidates`
- `POST /api/v1/memory/candidates/extract`
- `POST /api/v1/memory/candidates/from-report/{report_id}`
- `POST /api/v1/memory/candidates/from-task-run/{run_id}`
- `POST /api/v1/memory/candidates/from-validation/{validation_id}`
- `POST /api/v1/memory/candidates/from-patch-apply/{apply_run_id}`
- `POST /api/v1/memory/candidates/{candidate_id}/refresh-validation`
- `POST /api/v1/memory/candidates/{candidate_id}/reject`
- `POST /api/v1/memory/candidates/{candidate_id}/mark-duplicate`
- `GET /api/v1/memory/candidates/{candidate_id}`
- `GET /api/v1/memory/candidates/{candidate_id}/evidence`
- `GET /api/v1/memory/candidates/{candidate_id}/trace`
- `GET /api/v1/memory/candidates/{candidate_id}/events`
- `GET /api/v1/memory/candidates`

Sprint 23 adds candidate-only engineering memory. Candidates require source, scope and evidence for technical memory, pass sensitivity scanning, dedupe and conflict checks, and are stored as sanitized JSON under runtime candidate storage. Approved memory, vectorstore writes, embeddings, RAG ingestion, raw logs, secrets, full file content and automatic learning remain disabled. Chat can suggest or create a candidate, but cannot approve memory.

## Curated Engineering Memory

- `GET /api/v1/memory/status`
- `GET /api/v1/memory/curated/status`
- `POST /api/v1/memory/approvals/from-candidate/{candidate_id}`
- `POST /api/v1/memory/approvals/{approval_id}/persist`
- `POST /api/v1/memory/curated/from-candidate/{candidate_id}`
- `GET /api/v1/memory/curated/{memory_id}`
- `GET /api/v1/memory/curated/{memory_id}/versions`
- `GET /api/v1/memory/curated/{memory_id}/evidence`
- `GET /api/v1/memory/curated/{memory_id}/trace`
- `GET /api/v1/memory/curated/{memory_id}/events`
- `POST /api/v1/memory/curated/{memory_id}/supersede`
- `POST /api/v1/memory/curated/{memory_id}/expire`
- `POST /api/v1/memory/curated/{memory_id}/reject`
- `POST /api/v1/memory/curated/search`
- `GET /api/v1/memory/curated`

Sprint 24 enables explicit curated engineering memory persistence. A candidate is not memory. Persistence requires a valid candidate, source, evidence, scope, dedupe/conflict resolution, `curated_memory_persist` approval, operator confirmation and the explicit persist endpoint. Curated memory remains deterministic JSON storage only; vectorstores, embeddings, RAG ingestion, raw logs, secrets, full file content, automatic prompt injection and automatic chat injection remain disabled.

## Governed Read-Only Retrieval

- `GET /api/v1/rag/status`
- `GET /api/v1/rag/sources`
- `GET /api/v1/rag/sources/{source_id}`
- `POST /api/v1/rag/retrieve`
- `POST /api/v1/rag/retrieve/files`
- `POST /api/v1/rag/retrieve/reports`
- `POST /api/v1/rag/retrieve/memory`
- `POST /api/v1/rag/context-bundle`
- `POST /api/v1/rag/evidence-bundle`
- `POST /api/v1/rag/validate-citations`
- `GET /api/v1/rag/retrievals`
- `GET /api/v1/rag/retrievals/{retrieval_id}`
- `GET /api/v1/rag/retrievals/{retrieval_id}/trace`
- `GET /api/v1/retrieval/status`

Sprint 25 adds deterministic, source-scoped and citation-required retrieval. The allowed sources are project files through the read-only sandbox, project reports, task results, validation results, patch apply results and explicitly requested curated memory. Generic retrieval requires an explicit registered source. Vectorstore creation, embeddings, automatic ingestion, legacy RAG, web retrieval, raw logs, secrets, automatic chat retrieval and automatic prompt injection remain disabled.
