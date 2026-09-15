# GitHub Folder-by-Folder Genome Audit - 2026-09-15

Remote main was scanned before generation at 6126a73a9ddfc054fe527174fe4df16740b9d1e0. GitHub recursive tree returned 18,529 nodes with truncated=false; the local generator runs from the same Git object.

| Area | Current role | Classification |
|---|---|---|
| src/aipinho/services/runtime | TaskRuntime lifecycle, loop, timeline, Truth and phase admission | mixed CANONICAL / COMPATIBILITY / DIAGNOSTIC |
| src/aipinho/services/governance | public lifecycle, contract, policy, approval, SpeakerTruth, readonly boundary | CANONICAL / SPECIALIZED_CHILD |
| src/aipinho/services/semantics | semantic Sprints 0-9 chain | CANONICAL |
| src/aipinho/services/semantic_runtime | prompt semantic ingress and bounded interpreter | CANONICAL / SUPPORTING |
| src/aipinho/services/roles | role policy/model gates and TaskRuntime-bound role pipeline | SPECIALIZED_CHILD / SUPPORTING |
| src/aipinho/services/validation | validation gates and validators | CANONICAL / SUPPORTING |
| src/aipinho/api/routers | public/operator surfaces | ADAPTER / SUPPORTING |
| src/aipinho/schemas | runtime/public contracts | SPECIFICATION |
| config/runtime + config/roles + config/semantic_runtime | active runtime specification | SPECIFICATION |
| tests | validation evidence | TEST_ONLY |
| reports | bounded historical/current evidence | EVIDENCE |
| docs + Context Pack | orientation/handoff | ORIENTATION |
| genome | generated design DNA snapshot | GENERATED |
| quarantine / legacy_rag | retired/legacy namespace | LEGACY |

## Reachability corrections

- RuntimeDispatcherV2 and RuntimeContractsV2Service are reached from Runtime Operator inventory/tests, not the canonical TaskRun execution line.
- IntelligentPlannerService, ExecutionGraphService and ContinuousRuntimeService are instantiated by TaskRuntimeService, but GitHub code search found no subsequent self-attribute consumption in the canonical TaskRun path; Genome classifies them as compatibility/inventory.
- ReadonlyAnalysisArtifactRuntimeService is live but lifecycle/result terminalization/RuntimeTruth remain owned by TaskRuntime.
- Governed RolePipelineRun requires parent TaskRun/operation/execution binding; roles cannot become a parallel runtime or a sixth authority.
