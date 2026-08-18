# Asset Placeholder Generator

AssetPlaceholderGenerator creates local placeholder assets for templates without network access.

Current capability:

- Android vector XML placeholders with sanitized filenames.

Generated assets include an AssetManifest with:

- `asset_id`
- `filename`
- `asset_type`
- `format`
- `source`
- `template_id`
- `size_bytes`
- sanitized metadata

Placeholders are explicitly marked as replaceable and should not be treated as production art.
