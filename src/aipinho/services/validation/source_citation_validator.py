from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, contains_secret, finding

class SourceCitationValidator:
    def validate_evidence(self, evidence: Any) -> list:
        item = as_dict(evidence)
        findings = []
        source_type = str(item.get("source_type") or "")
        if source_type == "file" and not item.get("path"):
            findings.append(finding("invalid_evidence", "File evidence missing path", "File evidence requires a source path.", severity="error", validator="source_citation", blocking=True))
        if not (item.get("excerpt") or item.get("line_start") or source_type in {"metadata", "tree", "absence", "policy"}):
            findings.append(finding("invalid_evidence", "Evidence missing excerpt or line range", "Evidence should contain excerpt or line range unless it is metadata/tree/absence evidence.", severity="warning", validator="source_citation"))
        if contains_secret(item):
            findings.append(finding("secret_leak", "Secret-like evidence", "Evidence contains secret-like material and cannot pass quality gate.", severity="critical", validator="source_citation", blocking=True))
        return findings

    def status(self): return {"status": "ok", "service": "source_citation_validator"}
