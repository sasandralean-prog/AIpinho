from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.policy_bypass_detection_result import PolicyBypassDetectionResult
from aipinho.utils.yaml_loader import load_yaml_file


class PolicyBypassDetector:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "policy_bypass_detection_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")

    def detect(self, diff_text: str) -> PolicyBypassDetectionResult:
        patterns = [str(item).lower() for item in (self.policy.get("bypass_patterns", []) or [])]
        findings: list[PatchQualityFinding] = []
        added = [line[1:] for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")]
        for line_index, line in enumerate(added, start=1):
            lowered = line.lower()
            for pattern_index, pattern in enumerate(patterns, start=1):
                if pattern in lowered:
                    findings.append(PatchQualityFinding(finding_id=f"policy_bypass_{line_index}_{pattern_index}", category="policy_bypass", severity="critical", message=f"Possivel bypass de policy detectado: {pattern}", line=line_index, blocking=True))
        return PolicyBypassDetectionResult(status="rejected" if findings else "ok", bypass_signals=len(findings), findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "policy_bypass_detector", "execution_enabled": False}
