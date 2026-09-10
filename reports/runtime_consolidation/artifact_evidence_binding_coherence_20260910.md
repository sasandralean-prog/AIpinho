# Artifact Evidence Binding Coherence

## Conclusion

The live `ARTIFACT_EVIDENCE_BINDING_MISSING` was caused by a counting-semantics mismatch, not by loss of row evidence. Semantic selection bound 1305 entities, while the perception row model rendered 1263 rows. All 1263 rendered rows carried evidence references and row validation reported 1263/1263. The sufficiency service divided the rendered numerator by the selection denominator (1263/1305), producing a false 0.9678 ratio.

The fix keeps selection binding (`bound_rows / selected_rows`) separate from rendered-row evidence (`rows_with_evidence_ref / rows_rendered`). A genuine missing selection binding or rendered row reference remains fail-closed.

## Lineage

`ObservedEntity.evidence_refs` -> `SemanticEntitySelectionService` row binding -> perception candidate set -> CSV `evidence_ref` -> `RowLevelSemanticValidationService` -> `MediaInventorySufficiencyService` -> artifact projection -> `PhaseSemanticCompletionPolicy` -> RuntimeTruth/SpeakerTruth.

The 42 skipped candidates were library-root administrative/runtime files (licenses, runtime metadata, `.gitignore`, wrapper/runtime files) lacking the media contract attributes. They were not missing evidence from rendered rows.

## Binding taxonomy

- Entity/row provenance binding: entity id, source root, path and evidence reference.
- Technical observation binding: probe/metadata attempt and its evidence state.
- Semantic claim binding: field value plus claim-level evidence; absent in the run for semantic identity.
- Artifact provenance binding: artifact id, task run, producer, storage and digest.

An evidence reference string is currently counted as row binding evidence; this path does not independently resolve `file:` references against an evidence-record registry. Post-compile checkpoint references do have separate resolution/integrity validation. This is a remaining contract limitation, not changed by this patch.

## Coherence

The artifact-level binary fields are legacy/full-contract projections: `status=blocked`, `validation_status=blocked`, and `safe_to_use=false` mean the CSV did not satisfy unrestricted/full semantic sufficiency. They do not erase the multidimensional use-safety result. `safe_for_catalog=true` and `safe_for_planning=true_with_limitations` are coherent because phase completion explicitly admits bounded catalog planning while forbidding full truth and destructive use. Phase validation is scoped to the Phase 1 contract and may therefore be `passed_with_limitations` while one artifact is blocked against its full contract.

The naming remains ambiguous for clients that inspect only `safe_to_use` or `artifact_status`; those consumers can reasonably read them as universal denial. No broad rename was made. The additive coverage fields make the two cardinality domains explicit without weakening any gate.

## Historical comparison

B3.10 used the same intentional multidimensional safety pattern: blocked legacy artifact projection alongside catalog-safe/planning-limited output and `completed_with_limitations`. The current run is materially complete in materialization (1263/1263 rows) but incomplete for semantic identity truth (0 rows with semantic identity evidence). It is not equivalent to B3.10 in all input details, but the safety model is consistent.

## Validation

Added regressions cover: complete rendered evidence with a larger selection domain; actual missing rendered evidence; and actual missing selection binding. Existing row validation, sufficiency, use-safety, phase completion and finalization tests were run. One unrelated pre-existing test failure remains in `test_full_evidence_and_metadata_coverage_allows_phase1_discovery_but_not_full_truth_when_fields_missing`; the changed cardinality path is identical for that fixture and the failure is caused by an empty `inventory_confidence` fixture.

No FireTest was rerun. The corpus and historical reports were not modified.
