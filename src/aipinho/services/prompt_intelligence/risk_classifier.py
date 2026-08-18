from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.intent.risk import RiskResult
from aipinho.utils.yaml_loader import load_yaml_file


class RiskClassifier:
    ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "risk_policy.yaml"
        self._config: dict[str, object] | None = None

    def load(self) -> "RiskClassifier":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        return self._config or {}

    def _raise(self, current: str, candidate: str) -> str:
        return candidate if self.ORDER[candidate] > self.ORDER[current] else current

    def classify(self, *, intent_type: str, actions: list[str], protected_workspace: bool, ambiguous: bool) -> RiskResult:
        risk_config = self.config.get("risk", {}) if isinstance(self.config.get("risk", {}), dict) else {}
        level = "low"
        reasons: list[str] = []
        for candidate in ("low", "medium", "high", "critical"):
            raw = risk_config.get(candidate, {}) if isinstance(risk_config.get(candidate, {}), dict) else {}
            if intent_type in (raw.get("intents", []) or []):
                level = self._raise(level, candidate)
                reasons.append(f"intent:{intent_type}")
            if any(action in (raw.get("actions", []) or []) for action in actions):
                level = self._raise(level, candidate)
                reasons.append(f"action:{candidate}")
        if protected_workspace:
            level = "critical"
            reasons.append("forbidden_root")
        if ambiguous and level == "low":
            level = "medium"
            reasons.append("ambiguity")
        return RiskResult(level=level, reasons=sorted(set(reasons)))

    def status(self) -> dict[str, object]:
        try:
            risk = self.config.get("risk", {}) if isinstance(self.config.get("risk", {}), dict) else {}
            return {"status": "ok", "levels": len(risk)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}