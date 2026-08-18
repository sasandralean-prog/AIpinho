from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest, RoleModelBinding, RolePromptContract
from aipinho.utils.yaml_loader import load_yaml_file


class RolePromptContractBuilder:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_prompt_contracts.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def build(self, binding: RoleModelBinding, request: RoleInferenceRequest, model_id: str) -> RolePromptContract:
        defaults = self.config.get("defaults", {}) if isinstance(self.config.get("defaults", {}), dict) else {}
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        output_contract = request.output_contract or binding.output_contract
        blocked: list[str] = []
        lowered = request.prompt.lower()
        if any(term in lowered for term in {"aplique patch", "apply patch", "salve arquivo", "execute shell", "git commit", "git push"}):
            blocked.append("forbidden_side_effect_instruction")
        prompt_text = "\n\n".join(
            [
                f"Role: {binding.role_id}",
                "Policy: no tools, no workspace write, no patch apply, no shell, no git, no network.",
                f"Output contract: {output_contract}",
                str(defaults.get("reminder", "Nao afirme execucao sem evidencia.")),
                f"User/task input:\n{request.prompt}",
                f"Context:\n{request.context}" if request.context else "Context: none",
            ]
        )
        return RolePromptContract(
            role_id=binding.role_id,
            model_id=model_id,
            output_contract=output_contract,
            prompt_text=prompt_text,
            safety_envelope={"rules": ["no_tools", "no_workspace_write", "no_patch_apply", "no_shell", "no_git", "no_network"]},
            policy_envelope={"role_cannot_expand_permissions": True, "contract": contracts.get(output_contract, {})},
            blocked_reasons=blocked,
        )

    def messages(self, contract: RolePromptContract) -> list[PromptMessage]:
        return [PromptMessage(role="system", content="You are an AIpinho role worker operating inside a strict contract."), PromptMessage(role="user", content=contract.prompt_text)]

    def status(self) -> dict[str, object]:
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        return {"status": "ok", "service": "role_prompt_contract_builder", "contracts": sorted(contracts)}
