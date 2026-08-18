from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.utils.yaml_loader import load_yaml_file


class PermissionStatusResponseService:
    """Grounded answer for AIpinho workspace/capability permission questions."""

    def respond(
        self,
        *,
        session_id: str | None,
        operation_id: str | None = None,
        operation_type: str = "permission_status",
    ) -> ChatResponse:
        workspace_service = WorkspaceRoleContractService().load()
        workspace_config = workspace_service.config
        artifact_policy = self._config("artifacts", "artifact_target_policy.yaml")
        patch_policy = self._config("patching", "patch_target_policy.yaml")
        tool_policy = self._config("policies", "governed_tool_execution_policy.yaml")

        artifact_roots = set(self._norm_list(((artifact_policy.get("targets") or {}).get("allowed_workspace_roots") or [])))
        patch_roots = set(self._norm_list(((patch_policy.get("targets") or {}).get("allowed_roots") or [])))
        tool_roots = set(self._norm_list(((tool_policy.get("governed_tool_execution") or {}).get("allowed_workspace_roots") or [])))

        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in workspace_config.get("workspaces", []) or []:
            if not isinstance(item, dict) or not item.get("root_path"):
                continue
            root = str(item["root_path"])
            seen.add(self._norm(root))
            decision = workspace_service.resolve(root, required=True)
            contract = decision.contract
            entries.append(
                {
                    "workspace_id": item.get("workspace_id"),
                    "root_path": root,
                    "role": contract.role if contract else item.get("role"),
                    "read_allowed": bool(contract.read_allowed if contract else False),
                    "write_allowed": bool(contract.write_allowed if contract else False),
                    "patch_allowed": bool((contract.patch_allowed if contract else False) and self._norm(root) in patch_roots),
                    "artifact_allowed": self._norm(root) in artifact_roots,
                    "shell_network_allowed": self._norm(root) in tool_roots,
                    "approval_required": bool(contract.approval_required if contract else item.get("approval_required", True)),
                    "source": "config/workspaces/workspace_registry.yaml",
                }
            )

        for root in sorted((artifact_roots | patch_roots | tool_roots) - seen):
            entries.append(
                {
                    "workspace_id": "config_only_root",
                    "root_path": root,
                    "role": "config_only",
                    "read_allowed": False,
                    "write_allowed": root in patch_roots or root in artifact_roots,
                    "patch_allowed": root in patch_roots,
                    "artifact_allowed": root in artifact_roots,
                    "shell_network_allowed": root in tool_roots,
                    "approval_required": True,
                    "source": "config/artifacts|patching|policies",
                }
            )

        message = self._message(entries, tool_policy)
        tool_cfg = tool_policy.get("governed_tool_execution") or {}
        registered_capabilities = [str(item) for item in tool_cfg.get("allowed_capabilities", []) or []]
        currently_allowed_actions = [str(item) for item in tool_cfg.get("allowed_actions", []) or []]
        currently_blocked_actions = [str(item) for item in tool_cfg.get("denied_actions", []) or []]
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=message,
            intent={
                "intent_type": operation_type,
                "requires_task": False,
                "requires_workspace": False,
                "requires_patch": False,
            },
            policy={
                "read_only": True,
                "approval_required_for": [],
                "registered_capabilities": registered_capabilities,
                "currently_allowed_actions": currently_allowed_actions,
                "approval_required_actions": [
                    "workspace_write",
                    "apply_patch",
                    "artifact_generation",
                    "governed_shell",
                ],
                "currently_blocked_actions": currently_blocked_actions,
                "required_preconditions": [
                    "registered_workspace",
                    "workspace_role_allows_action",
                    "policy_allows_action",
                    "preview_when_required",
                    "approval_when_required",
                    "validation_when_required",
                ],
                "sources": [
                    "config/workspaces/workspace_registry.yaml",
                    "config/artifacts/artifact_target_policy.yaml",
                    "config/patching/patch_target_policy.yaml",
                    "config/policies/governed_tool_execution_policy.yaml",
                ],
            },
            operation_id=operation_id,
            operation_type=operation_type,
            message_type="assistant_final_answer",
            evidence_refs=[
                {"type": "policy_config", "ref_id": "workspace_registry", "human_label": "workspace_registry.yaml"},
                {"type": "policy_config", "ref_id": "artifact_target_policy", "human_label": "artifact_target_policy.yaml"},
                {"type": "policy_config", "ref_id": "patch_target_policy", "human_label": "patch_target_policy.yaml"},
                {"type": "policy_config", "ref_id": "governed_tool_execution_policy", "human_label": "governed_tool_execution_policy.yaml"},
            ],
            model_used="policy_config",
            real_inference=False,
            fallback_used=False,
        )

    def _message(self, entries: list[dict[str, Any]], tool_policy: dict[str, Any]) -> str:
        read_roots = [item for item in entries if item["read_allowed"]]
        write_roots = [item for item in entries if item["write_allowed"] or item["patch_allowed"] or item["artifact_allowed"]]
        shell_roots = [item for item in entries if item["shell_network_allowed"]]
        tool_cfg = tool_policy.get("governed_tool_execution") or {}
        allowed_capabilities = ", ".join(str(item) for item in tool_cfg.get("allowed_capabilities", []) or []) or "nenhuma"
        allowed_actions = ", ".join(str(item) for item in tool_cfg.get("allowed_actions", []) or []) or "nenhuma"
        denied_actions = ", ".join(str(item) for item in tool_cfg.get("denied_actions", []) or []) or "nenhuma"

        return "\n".join(
            [
                "Permissoes atuais da AIpinho:",
                "",
                "Leitura permitida:",
                *self._lines(read_roots, mode="read"),
                "",
                "Escrita/patch/artifact governados:",
                *self._lines(write_roots, mode="write"),
                "- capacidade registrada nao significa acao liberada agora: preview, approval, role e validacao ainda sao avaliados por pedido.",
                "",
                "Shell/network governado:",
                *self._lines(shell_roots, mode="shell"),
                f"- capabilities permitidas: {allowed_capabilities}",
                f"- actions permitidas: {allowed_actions}",
                f"- actions negadas por policy: {denied_actions}",
                "",
                "Regras de seguranca:",
                "- escrita real exige preview/policy/approval/validacao quando aplicavel.",
                "- shell livre nao esta liberado; execucao usa allowlist/denylist, timeout e audit.",
                "- git/destructive routes continuam bloqueados por default.",
                "",
                "Fontes: config/workspaces/workspace_registry.yaml; config/artifacts/artifact_target_policy.yaml; config/patching/patch_target_policy.yaml; config/policies/governed_tool_execution_policy.yaml.",
            ]
        )

    def _lines(self, entries: list[dict[str, Any]], *, mode: str) -> list[str]:
        if not entries:
            return ["- nenhum root configurado para esta categoria."]
        lines: list[str] = []
        for item in entries:
            detail = []
            if mode == "write":
                if item["patch_allowed"]:
                    detail.append("patch")
                if item["artifact_allowed"]:
                    detail.append("artifact")
                if item["write_allowed"]:
                    detail.append("workspace_write")
            elif mode == "shell":
                detail.append("shell/network")
            else:
                detail.append("read")
            approval = "approval obrigatorio" if item["approval_required"] else "approval nao obrigatorio"
            lines.append(f"- {self._redact_personal_path(str(item['root_path']))} ({item['role']}; {', '.join(sorted(set(detail)))}; {approval})")
        return lines

    def _redact_personal_path(self, value: str) -> str:
        home = str(Path.home()).replace("/", "\\").rstrip("\\")
        normalized = value.replace("/", "\\")
        if normalized.lower() == home.lower():
            return r"C:\Users\[REDACTED]"
        if normalized.lower().startswith(home.lower() + "\\"):
            return r"C:\Users\[REDACTED]" + normalized[len(home):]
        return normalized

    def _config(self, section: str, name: str) -> dict[str, Any]:
        root = PATHS.config_root / section
        return load_yaml_file(root / name, critical=True, root=root)

    def _norm_list(self, values: list[Any]) -> list[str]:
        return [self._norm(str(item)) for item in values]

    def _norm(self, value: str) -> str:
        return str(Path(value)).replace("/", "\\").rstrip("\\")
