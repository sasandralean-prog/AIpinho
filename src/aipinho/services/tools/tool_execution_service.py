from __future__ import annotations

from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService


class ToolExecutionService:
    def __init__(self, read_only: ReadOnlyExecutionService | None = None, governed: GovernedToolExecutionService | None = None) -> None:
        self.read_only = read_only or ReadOnlyExecutionService()
        self.governed = governed or GovernedToolExecutionService()

    def execute_readonly(self, request: ToolExecutionRequest):
        return self.read_only.execute(request)

    def request_governed_approval(self, request: ToolExecutionRequest):
        return self.governed.request_approval(request)

    def execute_governed(self, request: ToolExecutionRequest):
        return self.governed.execute(request)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "read_only": self.read_only.status(),
            "governed": self.governed.status(),
        }
