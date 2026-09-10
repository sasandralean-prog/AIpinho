# Semantic Sufficiency Cost Boundary

## Scope

This report investigates the live boundary observed by
`firetest5_live_20260910T085207Z`. No FireTest rerun was performed and neither
the PinhoAbacaxi workspace nor the media corpus was touched.

Source campaign: `task_run_179ebf56e2ef4c3eb7da644972870dfa` /
`op_f1bd743638d24f0d82685337113b2970`.

## Observed live evidence

- CSV rendering completed `1263/1263` rows and `109881/109881` cells.
- CSV stream elapsed time was `154406 ms`; cell rendering was `147542 ms`.
- Indexed lookup was `297 ms`; index build was `140 ms`; fallback scans were `0`.
- The artifact budget remained `420 s`; the run blocked with
  `MUSIC_INVENTORY_SUFFICIENCY_EVALUATION_STALLED` at `420.219 s`.
- Event timestamps place `after_row_validation` at `06:00:13`,
  `before_metadata_coverage_summary` at `06:01:10`, and
  `after_metadata_coverage_summary` / `before_inventory_sufficiency` /
  `after_inventory_sufficiency` at `06:01:11`. The historical event stream did
  not contain a schema-specific checkpoint, so the exact exclusive duration
  of `schema_coverage` is not directly observed in that run.
- `MediaInventorySufficiencyService.evaluate()` consumes aggregate summaries;
  source inspection and the coarse event timestamps do not support it as the
  dominant cost.
- `ArtifactUseSafetyService.evaluate_catalog_artifact()` is also aggregate-only
  and was not observed as a material cost.

The large post-row-validation interval is therefore evidence for a cost before
the aggregate sufficiency decision, not proof that the sufficiency service
itself spent the full budget.

## Call graph

The relevant current path is:

```text
ReadonlyAnalysisArtifactRuntimeService._contract_tabular_collection_content
  -> RowLevelSemanticValidationService.summarize_csv
  -> ObservedEntityCompilationService.schema_coverage
  -> ReadonlyAnalysisArtifactRuntimeService._metadata_coverage_summary
  -> MediaInventorySufficiencyService.evaluate
       -> ArtifactUseSafetyService.evaluate_catalog_artifact
  -> ArtifactSemanticContractService.validate / semantic profile
```

`schema_coverage` is an aggregate projection after the CSV is complete. Before
this patch it called `value_for_field()` for every entity-field pair.
`value_for_field()` canonicalized the field repeatedly and could perform alias,
compact, and near-match comparisons against the alias table each time.

## Historical B3.10 comparison

The B3.10 evidence was reviewed from the ten requested reports. It recorded
`completed_with_limitations / CATALOG_READY_WITH_INFERRED_AND_UNKNOWN_IDENTITY`
with `safe_for_truth_claim=false`, `safe_for_catalog=true`, and
`safe_for_planning=true_with_limitations`, despite `ffprobe_installed=false`.
It did not promote inferred or candidate identity to observed truth.

| Component | B3.10 behavior | Current behavior | Structural/cost change | Semantic change | Classification |
|---|---|---|---|---|---|
| Row taxonomy | Produced governed row classes and counts | Produces row applicability/taxonomy summaries before final artifact projections | Current campaign has a larger post-CSV projection path; no evidence that taxonomy itself dominates the post-row interval | Same fail-closed identity distinctions | Observed |
| Identity resolution | Observed/inferred/candidate/not-applicable were retained separately | Current summaries retain those distinctions and pass aggregate confidence into sufficiency | No evidence of identity promotion; current cost issue is lookup projection | Candidate/inferred remain non-Truth | Observed |
| Field status | B3.10 emitted observed/inferred/candidate/unknown status audits | Current path reads governed maps and derives schema coverage | Previous schema coverage repeated canonicalization per entity-field pair | Coverage result preserved | Observed |
| Inventory confidence | B3.10 computed aggregate confidence (`0.7719` overall catalog, `0.1955` truth, `0.7903` planning) | Current sufficiency consumes `row_applicability.inventory_confidence` as an aggregate | No evidence of a new confidence scan in `evaluate()` | Safety semantics preserved | Observed |
| Semantic profile | B3.10 reached terminal limited completion | Current run reached the profile boundary after CSV completion but blocked before terminal limited completion | Current event attribution is too coarse to assign exclusive profile cost | No semantic promotion is allowed | Observed |
| Sufficiency | B3.10 reached `passed_with_limitations` for planning/catalog use | Current `evaluate()` is aggregate-only and source inspection is linear in summary inputs | Not proven to be dominant; current reason was checkpoint attribution | Same safety gates remain | Observed / not proven for cost |
| Use safety | B3.10 exposed catalog/planning safety while blocking full Truth/destructive use | Current `ArtifactUseSafetyService` performs the same bounded aggregate decision | Not a plausible explanation for 420 s from source shape | Same safety dimensions | Observed |
| Completion | B3.10 emitted one partial terminal event with `SpeakerTruth=false` | Current run emitted one blocked terminal event with `SpeakerTruth=false` | Current stall prevented the limited-completion path | No false success | Observed |

The historical comparison shows that semantic insufficiency alone is not a
sufficient explanation for the current stall. B3.10 had weaker physical tool
availability and still completed its aggregate confidence/use-safety decision.
The current path carries the same semantic distinctions but, before this patch,
added an avoidable repeated canonicalization cost in the post-CSV projection.

## Cost model and reproducer

The generic reproducer used `300` entities and `30` fields, including missing
fields that force the complete scan. It compared the old reference loop with
the new `schema_coverage()` implementation using identical semantic input:

| Measurement | Before | After |
|---|---:|---:|
| Semantic result | `partial` | `partial` |
| Entity-field checks | `9000` | `9000` |
| Elapsed | `6210.417 ms` | `20.26 ms` |
| Canonicalization strategy | per entity-field lookup | once per schema field |
| Fallback scans | not applicable | `0` |

The supported complexity model is:

```text
before: O(E * F * A)
after:  O(F * A + E * F)
```

where `E` is the entity count, `F` is the schema-field count, and `A` is the
bounded alias/compact/near-match work for one canonicalization. The new path
also stops checking a canonical field after its coverage has been established.

The exact live percentage of the 420-second budget attributable exclusively to
this method is not available because the source campaign predates the
schema-specific checkpoint. The new bounded `coverage_metrics` and
`before_schema_coverage` / `after_schema_coverage` checkpoints make that
exclusive cost observable on the next authorized run.

## Correction

`ObservedEntityCompilationService.schema_coverage()` now:

1. canonicalizes each requested schema field once;
2. indexes requested fields by canonical key;
3. reads `observed_attributes` and `inferred_attributes` directly;
4. preserves covered/missing field semantics and status handling;
5. records bounded counts and elapsed time without per-cell events.

The runtime now persists schema-specific checkpoints and the aggregate metrics.
No budget, row selection, provenance, evidence, safety decision, or Truth rule
was weakened. No rows are skipped by the correction.

## Competing hypotheses

- **Indexed lookup bypass:** disconfirmed for the CSV path by `fallback_scans=0`
  and low lookup time in the campaign.
- **Another per-cell lookup/render operation:** disconfirmed as the dominant
  post-CSV cost by the same metrics; CSV was complete and lookup was cheap.
- **Checkpoint/observability overhead:** not proven dominant; checkpoints are
  bounded and the large interval precedes the new schema-specific stage.
- **Repeated projection/materialization:** proven for canonical alias resolution
  in `schema_coverage` by source inspection, counters, and the generic
  reproducer.
- **Sufficiency or use-safety evaluation:** disconfirmed as the dominant cost by
  aggregate input shape and coarse stage timestamps; exact micro-timing remains
  unobserved.
- **UnicodeDecodeError:** not proven causal, contributing, or related to this
  cost boundary. It remains a separate investigation.
- **FFmpeg/FFprobe:** not changed and not used for this diagnosis; availability
  does not explain the source-level repeated canonicalization.

## Validation

- Generic schema coverage reproducer: passed, including semantic equivalence and
  scale counters.
- Focused semantic suite: `27 passed, 2 pre-existing failures`.
- Focused renderer/terminality suite: `32 passed`.
- Adjacent contract-driven perception test: failed on the candidate and failed
  identically on baseline `a843df9a...`; therefore pre-existing.
- Full unit suite: `2146 passed, 90 failed, 1 skipped`; failures are broad
  pre-existing repository issues, not candidate-only renderer regressions.
- Full suite collection remains blocked by the known missing
  `vector_rag_test_helpers` module.
- `python -m compileall -q src\\aipinho`: passed.
- `git diff --check`: passed.
- Anti-hardcode review of the production diff: passed.

## Safety and limits

The artifact budget remains `420` seconds. Truth, provenance, identity status,
unknown handling, use-safety, and terminal blocking semantics are unchanged.
The observer historical hydration issue is separate and unchanged by this
patch. A same-protocol live FireTest rerun is still required for live validation,
but must be authorized separately.
