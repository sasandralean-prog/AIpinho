from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService


class WorkspaceMetadataQueryService:
    """Read-only chat answer for lightweight workspace metadata questions."""

    def __init__(self, workspace_service: WorkspaceRoleContractService | None = None) -> None:
        self.workspace_service = workspace_service or WorkspaceRoleContractService().load()

    def respond(self, *, session_id: str | None, decision: ChatOperationDecision) -> ChatResponse:
        workspace = decision.workspace
        workspace_decision = self.workspace_service.resolve(workspace, required=True)
        contract = workspace_decision.contract
        if workspace_decision.status != "allowed" or contract is None or not contract.read_allowed:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message="Nao consegui consultar os metadados porque o workspace nao esta liberado para leitura.",
                intent={"intent_type": "workspace_metadata_query", "requires_task": False, "requires_workspace": True, "requires_patch": False},
                policy={
                    "read_only": True,
                    "workspace_write": False,
                    "block_reason_code": workspace_decision.reason,
                    "workspace_id": contract.workspace_id if contract else None,
                    "workspace_role": contract.role if contract else None,
                },
                operation_id=decision.operation_id,
                operation_type="workspace_metadata_query",
                message_type="blocked_policy_message",
                warnings=[workspace_decision.reason],
                requires_user_action=False,
                is_final_answer=True,
            )

        root = Path(str(workspace or "")).expanduser().resolve(strict=False)
        if not root.exists() or not root.is_dir():
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="degraded",
                message=f"Nao encontrei um diretorio legivel em {self._redact_personal_path(str(root))}. Nenhum arquivo foi criado.",
                intent={"intent_type": "workspace_metadata_query", "requires_task": False, "requires_workspace": True, "requires_patch": False},
                policy={"read_only": True, "workspace_write": False, "reason_code": "workspace_path_not_found"},
                operation_id=decision.operation_id,
                operation_type="workspace_metadata_query",
                message_type="assistant_degraded_answer",
                warnings=["workspace_path_not_found"],
            )

        requested_files = [str(item) for item in decision.metadata.get("requested_files", []) or []]
        entrypoint_patterns = [str(item) for item in decision.metadata.get("entrypoint_patterns", []) or []]
        file_results = self._requested_file_results(root, requested_files)
        entrypoints = self._entrypoints(root, entrypoint_patterns)
        top_level = self._top_level_summary(root)
        message = self._message(root, file_results, entrypoints, top_level)
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=message,
            intent={
                "intent_type": "workspace_metadata_query",
                "requires_task": False,
                "requires_workspace": True,
                "requires_patch": False,
            },
            policy={
                "read_only": True,
                "workspace_write": False,
                "approval_required_for": [],
                "workspace_id": contract.workspace_id,
                "workspace_role": contract.role,
                "requested_files": file_results,
                "entrypoints": entrypoints,
                "top_level_summary": top_level,
            },
            operation_id=decision.operation_id,
            operation_type="workspace_metadata_query",
            message_type="assistant_final_answer",
            evidence_refs=[
                {"type": "workspace_metadata", "ref_id": contract.workspace_id, "human_label": "Metadados do workspace"},
            ],
            model_used="workspace_metadata_query",
            real_inference=False,
            fallback_used=False,
        )

    def _requested_file_results(self, root: Path, requested_files: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for name in requested_files:
            if not name or any(separator in name for separator in ("/", "\\")):
                continue
            path = (root / name).resolve(strict=False)
            if path.parent != root:
                continue
            exists = path.exists()
            results.append({"name": name, "exists": exists, "kind": "directory" if path.is_dir() else "file" if exists else "missing"})
        return results

    def _entrypoints(self, root: Path, patterns: list[str]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pattern in patterns:
            if not pattern or pattern.startswith(("/", "\\")) or ".." in Path(pattern).parts:
                continue
            for path in sorted(root.glob(pattern)):
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                if relative in seen:
                    continue
                seen.add(relative)
                entries.append({"path": relative, "kind": "directory" if path.is_dir() else "file"})
                if len(entries) >= 20:
                    return entries
        return entries

    def _top_level_summary(self, root: Path) -> dict[str, Any]:
        files = 0
        directories = 0
        sample: list[str] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                directories += 1
            elif child.is_file():
                files += 1
            if len(sample) < 20:
                sample.append(child.name)
        return {"files": files, "directories": directories, "sample": sample}

    def _message(self, root: Path, file_results: list[dict[str, Any]], entrypoints: list[dict[str, Any]], top_level: dict[str, Any]) -> str:
        lines = [
            "Consulta read-only concluida. Nao criei arquivo e nao gerei relatorio.",
            "",
            f"Workspace: {self._redact_personal_path(str(root))}",
        ]
        if file_results:
            lines.extend(["", "Arquivos perguntados:"])
            for item in file_results:
                status = "sim" if item["exists"] else "nao"
                lines.append(f"- {item['name']}: {status}")
        if entrypoints:
            lines.extend(["", "Arquivos de entrada aparentes:"])
            lines.extend(f"- {item['path']} ({item['kind']})" for item in entrypoints)
        else:
            lines.extend(["", "Arquivos de entrada aparentes: nenhum dos padroes configurados apareceu no topo do workspace."])
        lines.extend(
            [
                "",
                f"Topo do workspace: {top_level['files']} arquivos e {top_level['directories']} pastas.",
            ]
        )
        if top_level.get("sample"):
            lines.append("Amostra: " + ", ".join(str(item) for item in top_level["sample"]))
        return "\n".join(lines)

    def _redact_personal_path(self, value: str) -> str:
        home = str(Path.home()).replace("/", "\\").rstrip("\\")
        normalized = value.replace("/", "\\")
        if normalized.lower() == home.lower():
            return r"C:\Users\[REDACTED]"
        if normalized.lower().startswith(home.lower() + "\\"):
            return r"C:\Users\[REDACTED]" + normalized[len(home):]
        return normalized
