from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.evaluation_finding import EvaluationFinding
from aipinho.services.evaluation.evidence_requirement_validator import EvidenceRequirementValidator
from aipinho.utils.yaml_loader import load_yaml_file


class HallucinationSignalDetector:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "hallucination_signal_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.evidence = EvidenceRequirementValidator()

    def detect(self, content: str, evidence_context: list[dict[str, Any]] | None = None, system_status: dict[str, Any] | None = None) -> list[EvaluationFinding]:
        evidence_context = evidence_context or []
        system_status = system_status or {}
        findings: list[EvaluationFinding] = []
        evidence_paths = self.evidence._evidence_paths(evidence_context)
        for ref in EvidenceRequirementValidator.FILE_REF_PATTERN.findall(content):
            normalized = ref.replace("\\", "/")
            if evidence_paths and normalized not in evidence_paths:
                findings.append(EvaluationFinding(code="claims_unseen_files", severity="medium", message=f"Referenced file not present in evidence: {normalized}", source="hallucination_signal_detector"))
        lowered = content.lower()
        unavailable_terms = ["rag real", "memoria persistente", "memória persistente", "vectorstore real", "modelo real ativo"]
        disabled_markers = str(system_status).lower()
        if any(term in lowered for term in unavailable_terms) and ("disabled" in disabled_markers or not system_status):
            findings.append(EvaluationFinding(code="claims_unavailable_features", severity="medium", message="Response claims unavailable feature as active.", source="hallucination_signal_detector"))
        if re.search(r"\b\d{3,}\b", content) and not evidence_context:
            findings.append(EvaluationFinding(code="unsupported_specific_numbers", severity="low", message="Response uses specific numbers without evidence context.", source="hallucination_signal_detector"))
        if "arquitetura" in lowered and not evidence_context:
            findings.append(EvaluationFinding(code="unsupported_architecture_claim", severity="medium", message="Response describes architecture without evidence context.", source="hallucination_signal_detector"))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "hallucination_signal_detector", "enabled": True}
