from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ToolsSkillsAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("tools_skills", ["/api/v1/tools/status", "/api/v1/skills/status", "/api/v1/skills/preview"], "healthy", "Tools/skills aparecem como dry-run/preview e permissoes.")

