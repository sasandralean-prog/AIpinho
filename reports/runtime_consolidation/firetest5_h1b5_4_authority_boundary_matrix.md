# H1B5.4 Authority Boundary Matrix

| Authority | Can decide | Cannot decide | Inputs | Outputs | Evidence produced | Truth authority? |
|---|---|---|---|---|---|---|
| CapabilityRegistry | Which relationship capabilities are declared and available | Relationship truth, artifact rendering, validation pass | Registered `ObservationCapability` descriptors | Matching relationship capability descriptors | None | No |
| CapabilityArbitration | Whether a matching governed capability can be selected | Final relation, Speaker Truth, renderer behavior | RelationshipGoal, selected entities, capability descriptors, preconditions | Capability match/block reason | Audit metadata only | No |
| `media_relationship_candidate_detector` | Candidate/evidence/observation production from generic signals | Final validation, Truth, Completion, renderer materialization | ObservedEntity, RelationshipGoal, artifact contract, registry-selected capability id | RelationshipCandidate, RelationshipEvidenceSignal, RelationshipObservation, RelationshipProvenanceTrace, EvidenceRecord | `EvidenceRecord(evidence_type=relationship_observation)` | No |
| EvidenceRecord/EvidenceSet | Preserve evidence and provenance references | Decide relation validity or Truth | Attribute/relationship observations and execution results | Evidence records, evidence set summaries | Canonical evidence records | No |
| ArtifactSemanticProfile | Bind observed relationship evidence to artifact semantics | Observe filesystem, call detector, declare final relation Truth | Declared contract, perception payload, evidence records, relationship binding | Relationship summaries, gaps, validation readiness summaries | None | No |
| ArtifactSemanticContractService | Validate artifact semantics and expose contract gaps | Complete task, speak final relation, mutate artifact | Artifact bytes, declared contract, profile/perception payload | ArtifactSemanticProfile, contract validation result | None | No |
| Renderer | Materialize declared fields from profile/perception payload | Observe filesystem for relationships, infer relationships, call detector, create EvidenceRecord | `perception_payload`, declared fields, selected entities | Artifact fields/cells, render gaps | None | No |
| RelationshipValidationPolicyService | Evaluate readiness state from observations, provenance and EvidenceRecord | Speaker Truth, Completion, final claim authority | RelationshipObservation, RelationshipProvenanceTrace, relationship EvidenceRecord, policy | RelationshipValidationResult, validation summary | None | No |
| Validation/SemanticSelfReview | Identify whether evidence is sufficient for validation gates | Override missing evidence, infer final relationship, complete task | EvidenceSet, semantic assertions, relationship records | Quality questions, blocking reason codes | None | No |
| Completion | Decide task completion against Success Contract | Use relationship candidates as final Truth | Validation results, task artifacts, success contract | Completion status | None | No |
| Speaker Truth | Report only safe claims after governed validation/completion | Declare relationship final from candidate, confidence, validation_ready or validated alone | Validation/Completion/Speaker Truth inputs | Safe/blocked response truth state | None | Yes, only after gates pass |
| CVL/Fase 0 | Predict cognitive frontiers before runtime | Execute runtime, create TaskRun, decide operational Truth | FireTestProfile metadata, coverage, capability availability, relationship_cognition state | Cognitive predictions and coverage | None | No |

## Boundary Notes

- `validation_ready` is a readiness state, not Truth.
- `validated` from `RelationshipValidationPolicyService` still has `truth_eligible=false` and `speaker_claim_allowed=false`.
- Renderer is a materializer only.
- Missing `EvidenceRecord` now blocks readiness with `RELATIONSHIP_CANONICAL_EVIDENCE_RECORD_MISSING`.
