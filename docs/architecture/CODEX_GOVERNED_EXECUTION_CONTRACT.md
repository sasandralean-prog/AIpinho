# Codex Governed Execution Contract

## Purpose

The Codex CLI remains a proposal and reasoning provider. Side effects are owned by
AIpinho governance services.

The contract permits only three explicit action types:

- `create_file`
- `modify_file`
- `run_shell`

Delete, move, unrestricted shell, git write and implicit filesystem mutation are
not part of this contract.

## Lifecycle

1. `proposal`
   - Codex CLI runs with `--sandbox read-only`.
   - Structured output is validated against
     `config/codex_agent/governed_contract_output.schema.json`.
2. `preview`
   - Workspace role, target path, secret policy, limits and shell policy are
     evaluated.
   - No approval or side effect occurs.
3. `approval_pending`
   - Every action receives an independent approval.
   - File approvals bind the exact action fingerprint.
   - Shell approvals are created by `GovernedToolExecutionService`.
4. `approved`
   - All approvals are current and approved.
   - The contract and action fingerprints still match.
5. `executing`
   - Shell runs through the governed tool executor with argv, timeout,
     allowlist/denylist and audit.
   - File changes pass through `WriteCapabilityEnvelopeService`, atomic write,
     snapshot validation and rollback support.
6. `completed`
   - Every action completed and post-validation passed.
7. `blocked` or `failed`
   - No false success is reported.
   - File changes already made by the contract are rolled back when configured.

## Integrity

The contract fingerprint includes:

- objective;
- normalized workspace path;
- ordered action fingerprints.

Each action fingerprint includes:

- action type;
- workspace;
- target path;
- requested content hash;
- original file hash;
- argv;
- timeout.

Changing any approved value invalidates execution.

## Workspace Rules

Execution is allowed only for workspace roles configured in:

`config/codex_agent/codex_governed_execution_policy.yaml`

The default allowed roles are:

- `target_mutable`
- `system_mutable`

`source_readonly`, `protected`, `forbidden` and unregistered workspaces cannot
receive file changes from this contract.

## Shell Rules

The contract does not implement a shell adapter. It delegates to:

`GovernedToolExecutionService`

Therefore shell execution inherits:

- executable allowlist and denylist;
- command category policy;
- metacharacter blocking;
- workspace allowlist;
- timeout;
- exact approval fingerprint;
- audit;
- `shell=False`.

## API

- `GET /api/v1/codex-agent/governed/status`
- `POST /api/v1/codex-agent/sessions/{session_id}/contracts/propose`
- `POST /api/v1/codex-agent/sessions/{session_id}/contracts`
- `GET /api/v1/codex-agent/sessions/{session_id}/contracts`
- `GET /api/v1/codex-agent/contracts/{contract_id}`
- `POST /api/v1/codex-agent/contracts/{contract_id}/request-approval`
- `POST /api/v1/codex-agent/contracts/{contract_id}/refresh-approvals`
- `POST /api/v1/codex-agent/contracts/{contract_id}/execute`
- `POST /api/v1/codex-agent/contracts/{contract_id}/cancel`

File content is hidden from standard contract responses. It is returned only
when `include_content=true` is explicitly requested on the contract detail
endpoint.

## Non-goals

- No implicit execution from Codex chat.
- No free-form shell string execution.
- No delete or move operation.
- No git commit or push.
- No approval reuse across different actions.
- No write to read-only or forbidden workspaces.
- No success without post-validation.
