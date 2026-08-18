from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.evidence_validation import EvidenceValidationResult
from aipinho.utils.yaml_loader import load_yaml_file


class EvidenceRequirementValidator:
    FILE_REF_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.-]+\.(?:py|md|yaml|yml|json|txt|toml)")

    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "evidence_validation_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def _contract_requires_evidence(self, output_contract: dict[str, Any] | None) -> bool:
        contract = output_contract or {}
        return bool(contract.get("require_evidence") or contract.get("require_evidence_refs"))

    def _evidence_ids(self, evidence_context: list[dict[str, Any]]) -> set[str]:
        ids: set[str] = set()
        for item in evidence_context:
            for key in ("evidence_id", "id", "source_id"):
                if item.get(key):
                    ids.add(str(item[key]))
        return ids

    def _evidence_paths(self, evidence_context: list[dict[str, Any]]) -> set[str]:
        paths: set[str] = set()
        for item in evidence_context:
            for key in ("path", "file", "source", "relative_path"):
                if item.get(key):
                    paths.add(str(item[key]).replace("\\", "/"))
        return paths

    def _findings_from_content(self, content: str) -> list[dict[str, Any]]:
        stripped = content.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, dict) and isinstance(parsed.get("findings"), list):
            return [item for item in parsed["findings"] if isinstance(item, dict)]
        return []

    def validate(self, content: str, output_contract: dict[str, Any] | None = None, evidence_context: list[dict[str, Any]] | None = None) -> EvidenceValidationResult:
        evidence_context = evidence_context or []
        required = self._contract_requires_evidence(output_contract)
        evidence_ids = self._evidence_ids(evidence_context)
        evidence_paths = self._evidence_paths(evidence_context)
        missing: list[str] = []
        warnings: list[str] = []
        violations: list[str] = []
        findings = self._findings_from_content(content)
        if required:
            if findings:
                for index, finding in enumerate(findings):
                    refs = finding.get("evidence_ids") or finding.get("evidence_id") or finding.get("evidence") or finding.get("source")
                    refs_list = refs if isinstance(refs, list) else [refs] if refs else []
                    if not refs_list:
                        missing.append(f"finding_{index}")
                    elif evidence_ids and not any(str(ref) in evidence_ids for ref in refs_list):
                        missing.append(f"finding_{index}:unknown_evidence")
            elif evidence_context:
                if not any(str(eid) in content for eid in evidence_ids) and not any(path in content.replace("\\", "/") for path in evidence_paths):
                    missing.append("response_missing_evidence_reference")
            else:
                missing.append("evidence_context_required")
        unseen: list[str] = []
        for match in self.FILE_REF_PATTERN.findall(content):
            normalized = match.replace("\\", "/")
            if evidence_paths and normalized not in evidence_paths:
                unseen.append(normalized)
        if unseen:
            warnings.append("unseen_file_reference")
        violations = ["missing_required_evidence:" + item for item in missing]
        return EvidenceValidationResult(
            valid=not violations,
            required=required,
            evidence_ids_seen=sorted(evidence_ids),
            missing_evidence_claims=missing,
            unseen_file_refs=list(dict.fromkeys(unseen)),
            violations=violations,
            warnings=warnings,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evidence_requirement_validator", "enabled": True}
