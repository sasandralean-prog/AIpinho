# AIpinho Genome Summary

Generated: 2026-09-15T21:50:50.419424Z
Source main SHA: 6126a73a9ddfc054fe527174fe4df16740b9d1e0
Genome version: 2.0

Generated orientation only. Code, canonical config/contracts and validated runtime evidence outrank this Genome.

## Current architecture

Canonical path: public chat ingress -> CanonicalPublicChatService -> semantic intent/governance -> durable TaskRun -> TaskRunPlanner -> semantic vocabulary/graph/demand -> SupervisedExecutionLoop -> governed steps and TaskRuntime-bound role children -> evidence/validation -> semantic offer/compatibility -> completion -> RuntimeTruth -> CanonicalOperationState -> SpeakerTruth.

Genome v2 separates canonical authority from compatibility/inventory, specialized child execution, diagnostics, legacy code, evidence and test-only surfaces. RuntimeDispatcherV2 and PlannerV2 are not a second runtime.

## Validated baseline

- FireTest consolidation: Phase 1 partial/limited-use; Phases 2-6 completed.
- Timeline gaps/duplicates: 0/0 across all six phases.
- Runtime Doctor passed all six phases.
- Consolidated regression after reboot: 174 passed / 0 failed.
- Workspace/corpus mutations: 0 / 0.
- Deferred: Windows subprocess cp1252/.m4a media probe reader issue.

## Inventory

{
  "tracked_files": 18014,
  "python_modules": 2408,
  "services": 1214,
  "schemas": 942,
  "repositories": 52,
  "registries": 47,
  "router_modules": 138,
  "endpoints": 1086,
  "test_files": 1018,
  "test_functions": 3183
}
