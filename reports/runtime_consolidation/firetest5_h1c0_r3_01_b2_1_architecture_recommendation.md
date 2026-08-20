# H1C0.R3.01 B2.1 Architecture Recommendation

## Decision

Root cause is proven enough to reject a budget-only fix.

The next implementation slice should target the post-compile observation materialization boundary, not backend acquisition and not ffprobe installation.

## Minimal Truthful Retention Architecture

Retain inline:

- blocking semantic evidence
- media identity claim evidence
- requested optional enrichment evidence needed by the artifact contract
- compact provenance required to validate entity + canonical key + normalized value

Do not retain inline by default:

- unrequested generic metadata EvidenceRecords
- full raw/intermediate acquisition payloads
- repeated entity_ref objects in every aggregate position
- complete ObservationExecutionResult objects after their accepted evidence has been checkpointed

Preserve through refs/checkpoints:

- raw metadata support when needed for audit
- backend result provenance
- checksums or stable ids for replay
- policy-rejected evidence counts and reasons

## Option Comparison

### Option A: Contract/Demand-Aware Inline Filtering

Benefit: removes unrequested generic metadata and aligns retention with contract demand.

Risk: must not drop raw audit support before a durable reference exists.

Byte effect: useful but insufficient alone. The B2.1 model without inline metadata still estimates about 33.81 MB for the full corpus.

### Option B: Raw-Support EvidenceObject / Blob Ref

Benefit: preserves audit truth without copying raw support into every claim.

Risk: requires resolver, integrity, lifecycle and orphan handling.

Byte effect in current sample is small because metadata normalized_value averages 65.06 bytes, but this is important for future larger raw metadata.

### Option C: Checkpointed / Ref-Backed Post-Compile Results

Benefit: directly addresses the all-results-inline accumulation that blocked B2.

Risk: requires atomic commit semantics and validation must never consume missing refs.

This is required for a robust fix.

### Option D: Generic EvidenceSet Compaction

Benefit: material. `EvidenceSet.entity_refs` averaged 3,536.65 bytes per sampled result, and repeated per-record entity_ref averaged about 463-469 bytes.

Risk: consumers may currently expect inline entity_ref on each record. Add compatibility/resolver tests.

This is required or strongly recommended with Option C.

### Option E: Budget Increase Only

Rejected as primary fix. It preserves current inefficiency and weakens the guardrail without proving minimal retention.

## Required Tests For Next Slice

- semantic equivalence between old inline EvidenceSet and compact/ref-backed EvidenceSet
- no loss of entity_id/canonical_key/value/provenance binding
- missing ref blocks validation, not success
- policy-rejected result preserves physical telemetry
- produced vs accepted vs rejected evidence counts are distinct
- generic metadata can be omitted inline without satisfying or breaking identity claim truth
- endpoint summary uses physical authority when downstream artifact materialization is interrupted
- no endpoint hydrates heavy evidence payloads for status projection
- replay resolves compact/ref-backed evidence deterministically

## Recommended Next Experiment

Implement materialization compaction/ref-backed retention as a bounded slice, then rerun B2 under the same Mutagen-present / ffprobe-absent condition. Do not run C before this frontier is addressed.
