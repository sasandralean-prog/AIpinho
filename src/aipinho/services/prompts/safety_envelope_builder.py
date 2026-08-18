from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.prompts.safety_envelope import SafetyEnvelope
from aipinho.utils.yaml_loader import load_yaml_file


class SafetyEnvelopeBuilder:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "prompts" / "safety_envelopes.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def build(
        self,
        *,
        purpose: str,
        policy_decision: dict | None = None,
        role_id: str | None = None,
        output_contract_type: str | None = None,
    ) -> SafetyEnvelope:
        envelopes = self.config.get("envelopes", {}) if isinstance(self.config.get("envelopes", {}), dict) else {}
        rules: list[str] = []
        purpose_keys = ["default"]
        if purpose == "chat":
            purpose_keys.append("chat")
        if purpose == "project_report":
            purpose_keys.append("report_generation")
        if purpose in {"project_report", "code_analysis"}:
            purpose_keys.append("read_only_project_analysis")
        for key in purpose_keys:
            value = envelopes.get(key, {})
            if isinstance(value, dict):
                rules.extend([str(item) for item in value.get("rules", []) or []])
        status = str((policy_decision or {}).get("status", "unknown"))
        warnings: list[str] = []
        if status in {"denied", "blocked"}:
            rules.append("Policy status is denied/blocked: do not request execution and explain the block.")
            warnings.append("policy_denied_envelope")
        rules.append("Provider may be stub: do not claim real inference was used.")
        return SafetyEnvelope(
            envelope_id=f"safety_{uuid5(NAMESPACE_URL, purpose + ':' + status + ':' + str(role_id)).hex}",
            purpose=purpose,
            rules=list(dict.fromkeys(rules)),
            policy_status=status,
            read_only=True,
            real_inference=False,
            warnings=warnings,
        )

    def build_message(self, envelope: SafetyEnvelope) -> PromptMessage:
        content = "Safety envelope:\n" + "\n".join(f"- {rule}" for rule in envelope.rules)
        return PromptMessage(
            role="system",
            content=content,
            metadata={"envelope_id": envelope.envelope_id, "purpose": envelope.purpose},
        )

    def status(self) -> dict[str, object]:
        envelopes = self.config.get("envelopes", {}) if isinstance(self.config.get("envelopes", {}), dict) else {}
        return {"status": "ok", "service": "safety_envelope_builder", "envelopes": sorted(envelopes.keys())}
