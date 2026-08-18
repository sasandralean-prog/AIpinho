# Artifact Cleanup and Retention

Cleanup is preview-first.

Preserved:

- artifacts with evidence refs;
- final/preserved records;
- validation/promotion/report evidence.

Candidates:

- failed artifacts without evidence;
- expired artifacts without evidence;
- deleted records without evidence.

The current apply endpoint is intentionally conservative and returns a preview rather than deleting files without an explicit confirmation pipeline.
