from __future__ import annotations

from aipinho.schemas.patching.quality.hardcode_detection_result import HardcodeDetectionResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.utils.yaml_loader import load_yaml_file
from aipinho.core.paths import PATHS


class HardcodeDetector:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "hardcode_detection_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")

    def detect(self, diff_text: str) -> HardcodeDetectionResult:
        patterns = self.policy.get("patterns", {}) if isinstance(self.policy.get("patterns"), dict) else {}
        findings: list[PatchQualityFinding] = []
        added = [line[1:] for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")]
        all_patterns: list[tuple[str, str, bool]] = []
        for value in patterns.get("critical", []) or []:
            all_patterns.append((str(value), "critical", True))
        for value in patterns.get("warning", []) or []:
            all_patterns.append((str(value), "medium", False))
        for line_index, line in enumerate(added, start=1):
            for pattern_index, (pattern, severity, blocking) in enumerate(all_patterns, start=1):
                if pattern.lower() in line.lower():
                    findings.append(PatchQualityFinding(finding_id=f"hardcode_{line_index}_{pattern_index}", category="hardcode", severity=severity, message=f"Possivel hardcode operacional detectado: {pattern}", line=line_index, blocking=blocking))
        critical = sum(1 for item in findings if item.severity == "critical")
        status = "rejected" if critical else ("needs_review" if findings else "ok")
        return HardcodeDetectionResult(status=status, hardcodes_found=len(findings), critical_found=critical, findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "hardcode_detector", "execution_enabled": False}
