from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.quality.import_impact_result import ImportImpactResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.utils.yaml_loader import load_yaml_file


class ImportImpactAnalyzer:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "import_impact_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")

    def analyze(self, diff_text: str) -> ImportImpactResult:
        risky = [str(item) for item in (self.policy.get("risky_imports", []) or [])]
        changed: list[str] = []
        risky_found: list[str] = []
        findings: list[PatchQualityFinding] = []
        for line_index, line in enumerate(diff_text.splitlines(), start=1):
            if not line.startswith("+") or line.startswith("+++"):
                continue
            content = line[1:].strip()
            if content.startswith("import ") or content.startswith("from "):
                changed.append(content)
                for import_name in risky:
                    if import_name in content:
                        risky_found.append(import_name)
                        findings.append(PatchQualityFinding(finding_id=f"import_impact_{line_index}", category="import_impact", severity="medium", message=f"Import sensivel requer revisao: {import_name}", line=line_index, blocking=False))
        return ImportImpactResult(status="needs_review" if findings else "ok", changed_imports=changed, risky_imports=list(dict.fromkeys(risky_found)), requires_review=bool(findings), findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "import_impact_analyzer", "execution_enabled": False}
