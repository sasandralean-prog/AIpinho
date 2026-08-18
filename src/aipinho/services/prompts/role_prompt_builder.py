from __future__ import annotations

from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.prompts.prompt_template_service import PromptTemplateService


class RolePromptBuilder:
    def __init__(self, templates: PromptTemplateService | None = None) -> None:
        self.templates = templates or PromptTemplateService()

    def build_role_message(self, role_id: str) -> tuple[PromptMessage, list[str]]:
        template = self.templates.get_template(role_id)
        if template is None:
            return PromptMessage(role="developer", content="Role instruction unavailable. Operate conservatively and do not execute tools.", metadata={"role_id": role_id, "status": "degraded"}), ["unknown_role_template"]
        return PromptMessage(role="developer", content=template.instruction.strip(), metadata={"role_id": role_id}), []

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_prompt_builder", "templates": self.templates.status()}
