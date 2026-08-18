# H1C0.R2.17 Cell Lookup Deep Diagnostic

Root cause status: proven.

The hot cell path resolved metadata_status, metadata_source, and probe_status by calling _media_metadata_observations_for_entity, which scanned the full ttribute_observations list for each entity/cell. This creates an O(rows x metadata columns x observations) boundary. R2.17 adds a per-render immutable lookup context built from governed payload data once, then resolves cells by bounded lookup.

A/B timing ambiguity is resolved in iretest5_h1c0_r2_17_timing_semantics.json: Diagnostic A and Validation B used different timer coverage; R2.17 separates value lookup from normalization/render.
