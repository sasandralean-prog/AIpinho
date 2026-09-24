# Authority and Responsibility Map — AIpinho

## Canonical authority orientation

AIpinho's existing authority documentation remains canonical for current runtime details. At engineering level:

```text
human intent/authority
→ frozen mission/resource contract
→ canonical policy/governance
→ canonical TaskRuntime/domain owner
→ subordinate role/provider/tool/fallback
→ evidence + validation
→ RuntimeTruth / CanonicalOperationState / SpeakerTruth
```

The trusted dispatcher and local broker execute bounded already-authorized capabilities; they must remain semantically dumber than AIpinho. Roles/models are cognitive components, not a sixth authority.

## Conflict rule

When two components appear to own the same decision, do not patch both. Identify the canonical owner, characterize consumers, migrate evidence/behavior, and retire or subordinate the duplicate.

## Responsibility contract

For substantial subsystems record: `Owns`, `Consumes`, `Produces`, `May`, `Must not`, canonical dependencies, and evidence/telemetry.

A fallback selected by the canonical owner is legitimate. A fallback that bypasses that owner is a parallel flow.
