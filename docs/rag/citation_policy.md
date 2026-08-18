# Citation Policy

No retained retrieval hit may enter a context bundle without a valid `SourceRef` and `Citation`.

A citation contains:

- source id and type;
- stable source reference;
- bounded excerpt;
- content hash;
- location, section or field when available;
- evidence id when the source has one.

Supported citation types:

- `file_line_range`
- `report_section`
- `task_result_field`
- `validation_finding`
- `patch_apply_field`
- `memory_id`
- `evidence_id`

`SourceRefValidator` blocks missing references and empty excerpts. `EvidenceBundleBuilder` blocks bundles with missing or invalid citations. Prompt Assembly accepts retrieval context only when the bundle is explicitly marked safe and contains citations.
