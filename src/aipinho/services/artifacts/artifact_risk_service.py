from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_content import ArtifactContentValidation
from aipinho.schemas.artifacts.artifact_risk import ArtifactRiskAssessment
from aipinho.schemas.artifacts.artifact_target import ArtifactTargetValidation
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.utils.yaml_loader import load_yaml_file

RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
SCORE = {"low": 0.2, "medium": 0.5, "high": 0.75, "critical": 1.0}


class ArtifactRiskService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_risk_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.trace = ArtifactTraceService()

    def assess(self, target: ArtifactTargetValidation, content: ArtifactContentValidation) -> ArtifactRiskAssessment:
        reasons: list[str] = []
        level = "low"
        if target.would_overwrite:
            level = self._max(level, "medium")
            reasons.append("overwrite_existing")
        high_reasons = {"base_dir_not_allowed", "config_mutation_target"}
        critical_reasons = {"forbidden_root", "path_traversal", "outside_workspace", "source_code_target", "script_target", "blocked_extension", "extension_not_allowed", "secret_content", "binary_content", "executable_content"}
        for reason in [*target.blocked_reasons, *content.blocked_reasons]:
            if reason in critical_reasons:
                level = self._max(level, "critical")
                reasons.append(reason)
            elif reason in high_reasons:
                level = self._max(level, "high")
                reasons.append(reason)
            elif reason == "content_too_large":
                level = self._max(level, "medium")
                reasons.append(reason)
            elif reason:
                level = self._max(level, "high")
                reasons.append(reason)
        decisions = self.policy.get("decisions", {}) if isinstance(self.policy.get("decisions"), dict) else {}
        decision = decisions.get(level, {}) if isinstance(decisions.get(level), dict) else {}
        blocked = bool(decision.get("blocked", False)) or level == "critical"
        return ArtifactRiskAssessment(
            risk_level=level,  # type: ignore[arg-type]
            score=SCORE[level],
            approval_required=bool(decision.get("approval_required", True)),
            preview_allowed=bool(decision.get("preview_allowed", not blocked)),
            blocked=blocked,
            needs_review=bool(decision.get("needs_review", False)),
            reasons=list(dict.fromkeys(reasons)),
            trace=[self.trace.item("artifact_risk", "checked", "risk_policy_applied", source="config/artifacts/artifact_risk_policy.yaml", data={"risk_level": level, "reasons": reasons})],
        )

    def _max(self, current: str, candidate: str) -> str:
        return candidate if RANK[candidate] > RANK[current] else current

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_risk", "enabled": True}
