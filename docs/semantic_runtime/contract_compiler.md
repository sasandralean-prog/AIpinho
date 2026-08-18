# Contract Compiler

Sprint SR5 adds deterministic compilation from normalized ISR to canonical
runtime contracts.

The compiler does not call LLMs, executors, tools, skills, files, approvals, or
Runtime. It only creates contract objects.

## Flow

```text
Prompt
  -> Semantic Interpreter
  -> ISR
  -> Semantic Normalizer
  -> Contract Compiler
  -> Canonical Runtime Contracts
```

## Builders

- `ExecutionContractBuilder`
- `WorkspaceContractBuilder`
- `ApprovalContractBuilder`
- `ArtifactContractBuilder`
- `ValidationContractBuilder`
- `RoleContractBuilder`

## Versioning and Validation

- `ContractVersioning`
- `ContractValidator`

The current contract version is `1.0`.

## Feature Flag

`semantic_contract_pipeline.enabled` lives in:

`config/semantic_runtime/contract_compiler.yaml`

When enabled, the semantic pipeline can also expose an IntentMap-compatible
adapter for legacy Runtime compatibility. The adapter is derived from contracts,
not from the raw prompt.

## Boundary

SR5 does not implement Runtime Operator or Runtime Doctor.
