from __future__ import annotations

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.utils.yaml_loader import load_yaml_file
from aipinho.core.paths import PATHS


class DiffStatsValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "diff_parse_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")

    def validate(self, parse: DiffParseResult) -> list[PatchQualityFinding]:
        limits = self.policy.get("limits", {}) if isinstance(self.policy.get("limits"), dict) else {}
        max_files = int(limits.get("max_files", 10))
        max_changed = int(limits.get("max_changed_lines", 300))
        changed = parse.added_lines + parse.removed_lines
        findings: list[PatchQualityFinding] = []
        if len(parse.affected_files) > max_files:
            findings.append(PatchQualityFinding(finding_id="diff_stats_files_1", category="diff_stats", severity="high", message="Diff altera arquivos demais para revisao segura automatica.", blocking=True))
        if changed > max_changed:
            findings.append(PatchQualityFinding(finding_id="diff_stats_lines_1", category="diff_stats", severity="medium", message="Diff grande requer revisao humana ampliada.", blocking=False))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "diff_stats_validator", "execution_enabled": False}
