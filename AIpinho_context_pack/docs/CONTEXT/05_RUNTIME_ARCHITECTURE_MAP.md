# AIpinho Runtime Architecture Map

> Conceptual orientation only. Current code and validated public evidence remain authoritative.

## High-level chain
```text
User request
→ semantic ingress
→ intent resolution
→ operation contract
→ planning / IR
→ governed runtime
→ observation / perception
→ facts + provenance
→ artifact materialization
→ validation / completion
→ TaskRun terminal result
→ SpeakerTruth
→ user-facing claim
```

## Boundaries

### Semantic ingress
Interprets the request and classifies the operation. Request wording is not itself a runtime contract.

### Operation contract
Defines what is allowed, expected, and required. Execution should not outrun the contract.

### Governed runtime
Owns execution, checkpoints, budgets, and terminality. Accepted work must terminalize, and known-stage failure should preserve a specific reason.

### Observation / perception
Produces governed representations of observable reality and keeps missing, unsupported, failed, candidate, observed, and derived states distinct.

### Fact projection + source binding
Facts remain connected to evidence and provenance. Source identity must not be inferred from superficial locators.

### Artifact runtime
Materializes governed payloads. Renderer must not scan the filesystem to invent metadata.

### Persistence
R2 established bounded persist checkpoints, payload refs for large semantic subtrees, atomic content write, failure cleanup, sharded manifest/index behavior, and legacy registry outside the hot path.

### CSV/tabular materialization
R2.16–R2.17 established explicit cardinality domains, deterministic row/order digests, stall vs budget semantics, and indexed per-render cell lookup with public fallback scan reaching zero.

### Identity validation
R2.18 established:
- stable entity identity: `entity_id`;
- locator/display: filename/name/relative path;
- routing hints: extension/media type/root role;
- semantic media identity: title/artist/album-style claims requiring governed observation evidence.

### Completion
Completion is semantic, not merely operational. A blocked run can terminalize correctly without fulfilling the request.

### SpeakerTruth
Final communication boundary controlling what can safely be claimed.

## Important distinctions
```text
artifact created ≠ contract fulfilled
result persisted ≠ semantic success
candidate produced ≠ Truth
stable entity identity ≠ semantic media identity
evidence exists somewhere ≠ evidence supports this exact claim
```

## Current transition
R2 focused on reliable representation, execution, observation, terminality, materialization, and honest refusal.

R3 begins with a different problem: the representation exists, but public runtime lacks a configured governed capability to acquire semantic media identity evidence.
