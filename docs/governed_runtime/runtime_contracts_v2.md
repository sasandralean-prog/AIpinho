# Runtime Contracts V2

GR1 introduces explicit, versioned Runtime Contracts V2.

Runtime execution layers should receive contracts, not raw prompts or ISR
objects. The compatibility layer can convert SR5 semantic contracts into V2
runtime contracts while preserving legacy behavior behind a feature flag.

## Contracts

- `ExecutionContract`
- `WorkspaceContract`
- `ApprovalContract`
- `ArtifactContract`
- `ValidationContract`
- `RoleContract`
- `ToolContract`
- `SkillContract` placeholder
- `RuntimeContractBundle`

## Versioning

Every contract contains a `ContractVersion`.

The initial V2 version is `2.0`.

## Serialization

`ContractSerializer` provides stable JSON/dict serialization and restoration.

## Validation

`RuntimeContractValidator` enforces:

- no prompt/raw prompt/free execution text fields
- no compiler-enabled execution
- no approval ids created by compilation
- no tool invocation by default
- no skill invocation by default
- deterministic contracts

## Feature Flag

`governed_runtime_contracts_v2.enabled` lives in:

`config/runtime/runtime_contracts_v2.yaml`

When disabled, legacy Runtime behavior remains available.
