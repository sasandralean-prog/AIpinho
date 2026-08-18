from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.security_regression_result import SecurityRegressionResult
from aipinho.utils.yaml_loader import load_yaml_file


class SecurityRegressionDetector:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "security_regression_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")

    def detect(self, diff_text: str) -> SecurityRegressionResult:
        protected_terms = [str(item).lower() for item in (self.policy.get("protected_terms", []) or [])]
        findings: list[PatchQualityFinding] = []
        removed = [line[1:] for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")]
        for line_index, line in enumerate(removed, start=1):
            lowered = line.lower()
            for term_index, term in enumerate(protected_terms, start=1):
                if term in lowered:
                    findings.append(PatchQualityFinding(finding_id=f"security_regression_{line_index}_{term_index}", category="security_regression", severity="high", message=f"Remocao de termo protegido requer revisao: {term}", line=line_index, blocking=True))
        return SecurityRegressionResult(status="rejected" if findings else "ok", regression_signals=len(findings), findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "security_regression_detector", "execution_enabled": False}
