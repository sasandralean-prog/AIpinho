from __future__ import annotations

from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


class SandboxViewModelService:
    def view_model(self) -> dict[str, object]:
        service = SandboxWorkspaceService()
        status = service.status()
        workspaces = service.list_workspaces()
        tasks = service.list_tasks()
        active = [task for task in tasks if task.status in {"created", "running"}]
        return {
            "screen": "sandbox",
            "status": status.status,
            "title": "Sandbox Governado",
            "human_summary": "Sandbox local pronto para execucao livre dentro da caixinha de areia governada.",
            "root_path_sanitized": status.root_path_sanitized,
            "workspaces_count": len(workspaces),
            "tasks_count": len(tasks),
            "active_tasks_count": len(active),
            "artifacts_count": status.artifacts,
            "cards": [
                {
                    "card_id": "sandbox_status",
                    "title": "Estado do Sandbox",
                    "status": status.status,
                    "summary": f"{len(workspaces)} workspaces, {len(tasks)} tasks, {status.artifacts} artifacts.",
                },
                {
                    "card_id": "sandbox_policy",
                    "title": "Policy",
                    "status": "healthy",
                    "summary": "Leitura, escrita, shell seguro e artifacts sao permitidos somente dentro do sandbox.",
                },
            ],
            "safe_actions": [
                {"label": "Atualizar Sandbox", "method": "GET", "endpoint_ref": "/api/v1/mobile/view-model/sandbox", "side_effect": False},
                {"label": "Criar Workspace Sandbox", "method": "POST", "endpoint_ref": "/api/v1/sandbox/workspaces", "side_effect": True},
            ],
            "raw_default_visible": False,
        }
