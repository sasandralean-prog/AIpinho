# KR2 Module Runtime

Status: KR2_READY.

Runtime roles are represented as loadable `KernelModule` definitions with lifecycle operations:

- `initialize`
- `validate`
- `execute`
- `shutdown`
- `health`
- `metadata`

Module execution remains guarded and returns `not_executed` without a Runtime contract.

Validation:

- Module loader registered the canonical module set.
- Module lifecycle exposes initialize, validate, execute, shutdown, health and metadata.
- Execution remains guarded by Runtime contracts.
