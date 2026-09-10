# CSV Artifact Renderer Throughput Regression

## Scope

This report covers the generic CSV artifact renderer path. No FireTest rerun,
corpus mutation, budget change, or fixture-specific production logic was used.

## Evidence

The current campaign rendered 1,088 of 1,263 rows before the unchanged 420
second artifact budget was exhausted. The final checkpoint reported 94,662
cell lookups, 212,982 ms of cell render time, 33,902 ms of lookup time, 79 ms
of normalization/serialization time, 125 ms of index construction, and zero
fallback scans. This rules out the indexed attribute-observation fallback and
CSV serialization as the dominant cost.

R2.17 historical evidence rendered 55,750 cells in 92,063 ms, including
17,165 ms of lookup time and 14 ms of cell serialization, with zero fallback
scans and 61 ms index construction.

The hot path called `canonical_attribute_name()` for every cell. A generic
100,000-call benchmark measured 43,427.91 ms, approximately 434.28 us per
call. The call performs alias and compact-name normalization, so its cost is
proportional to rows times columns and alias candidates.

## Correction

The immutable per-render lookup context now contains a canonical field
projection built once from the render schema. Cell resolution reuses that
projection and retains the existing canonicalization fallback when called
without a render context. No values, provenance, evidence bindings, unknown
semantics, or row selection rules changed.

The cardinality regression fixture was also corrected to use a generic tabular
contract instead of a media-inventory contract that intentionally appends its
taxonomy columns. No production behavior was reduced to make the assertion
pass.

## Generic scale validation

| entities | observations | cells | reference canonicalization | projected index build | projected cell resolution | fallback scans |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 400 | 300 | 117.185 ms | 1.542 ms | 0.364 ms | 0 |
| 500 | 2,000 | 1,500 | 572.613 ms | 2.279 ms | 1.564 ms | 0 |
| 2,500 | 10,000 | 7,500 | 2,919.903 ms | 5.560 ms | 7.790 ms | 0 |

The scale test proves that canonical field resolution is bounded by the
render schema after context construction rather than repeated per-row
normalization. Existing indexed lookup tests prove semantic equivalence and
zero observation-list rescans.

## Separate observer issue

`OBSERVER_HISTORICAL_HYDRATION_MEMORY_BOUNDARY` remains a separate generic
change already present in the worktree: lightweight TaskRun index/projection
listing and observer behavior that avoids hydrating heavy historical payloads
for identity/status polling. It is not part of the CSV renderer correction.

## Validation state

- Focused renderer/lifecycle/terminality regression: PASS, 55 tests.
- Generic scale validation: PASS.
- Artifact budget: unchanged at 420 seconds.
- Rows skipped by the correction: none.
- Provenance and semantic contract: unchanged.
- Live FireTest rerun: not performed.
