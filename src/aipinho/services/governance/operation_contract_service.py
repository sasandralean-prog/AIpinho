from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.governance.operation_contract import OperationContract, OperationPermissionDecision
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.utils.yaml_loader import load_yaml_file


class OperationContractService:
    def __init__(
        self,
        *,
        policy_path: Path | None = None,
        permission_matrix: WorkspacePermissionMatrixService | None = None,
    ) -> None:
        self.policy_path = policy_path or PATHS.config_root / "policies" / "operation_contract_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=self.policy_path.parent)
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService().load()

    def build(
        self,
        *,
        source_channel: str,
        source_client: str = "unknown",
        session_id: str | None,
        user_text: str,
        intent_type: str,
        operation_type: str,
        requested_actions: list[str] | None = None,
        workspace_refs: list[str] | None = None,
        target_paths: list[str] | None = None,
        command: str | None = None,
        content: str | None = None,
        operation_id: str | None = None,
    ) -> OperationContract:
        actions = list(dict.fromkeys(str(item) for item in (requested_actions or []) if str(item).strip()))
        normalized_actions = self.normalize_actions(actions)
        constraints = self.extract_negative_constraints(user_text)
        refs = [str(item) for item in (workspace_refs or []) if str(item).strip()]
        targets = [str(item) for item in (target_paths or []) if str(item).strip()]
        resolved_path = refs[0] if refs else (self._workspace_from_targets(targets) if targets else None)
        decisions = self.decide_permissions(
            normalized_actions,
            resolved_path=resolved_path,
            target_paths=targets,
            negative_constraints=constraints,
        )
        approval_required = any(item.requires_approval for item in decisions)
        execution_allowed = bool(decisions) and all(item.decision == "allowed" for item in decisions)
        blocked = [item.reason_code for item in decisions if item.decision == "denied"]
        workspace_decision = self.permission_matrix.decide(path=resolved_path, permission="read_file") if resolved_path else None
        return OperationContract(
            operation_id=operation_id or f"op_{uuid4().hex}",
            source_channel=source_channel,
            source_client=source_client,
            session_id=session_id,
            user_text=user_text,
            intent_type=intent_type,
            operation_type=operation_type,
            requested_actions=actions,
            normalized_actions=normalized_actions,
            negative_constraints=constraints,
            workspace_refs=refs,
            resolved_workspace_id=workspace_decision.workspace_id if workspace_decision else None,
            resolved_workspace_path=workspace_decision.root_path if workspace_decision else resolved_path,
            target_paths=targets,
            command=command,
            content=content,
            risk_level=self._risk_level(normalized_actions),
            permission_decisions=decisions,
            approval_required=approval_required,
            execution_allowed=execution_allowed and not approval_required,
            execution_plan={
                "mode": "preview_approval_validation" if approval_required else ("execute_allowed" if execution_allowed else "blocked"),
                "blocked_reasons": blocked,
            },
            speaker_truth_requirements={
                "must_not_claim_execution_without_result": True,
                "must_show_approval_when_required": approval_required,
                "must_show_block_reason_when_denied": bool(blocked),
            },
            warnings=blocked,
            trace=[
                {
                    "stage": "operation_contract",
                    "source": "OperationContractService",
                    "policy": str(self.policy_path),
                    "actions": actions,
                    "normalized_actions": normalized_actions,
                    "resolved_path": resolved_path,
                }
            ],
        )

    def normalize_actions(self, actions: list[str]) -> list[str]:
        aliases = self.policy.get("action_aliases", {}) or {}
        normalized: list[str] = []
        for action in actions:
            mapped = aliases.get(action, [action])
            if isinstance(mapped, str):
                mapped = [mapped]
            for item in mapped:
                value = str(item)
                if value not in normalized:
                    normalized.append(value)
        return normalized

    def extract_negative_constraints(self, text: str) -> dict[str, bool]:
        normalized = self._normalize_text(text)
        constraints: dict[str, bool] = {}
        for key, config in (self.policy.get("negative_constraints", {}) or {}).items():
            terms = config.get("terms", []) if isinstance(config, dict) else []
            if any(self._normalize_text(str(term)) in normalized for term in terms):
                constraints[str(key)] = bool(config.get("value", True))
        return constraints

    def decide_permissions(
        self,
        actions: list[str],
        *,
        resolved_path: str | None,
        target_paths: list[str],
        negative_constraints: dict[str, bool],
    ) -> list[OperationPermissionDecision]:
        decisions: list[OperationPermissionDecision] = []
        permission_aliases = self.policy.get("permission_aliases", {}) or {}
        blocked_actions = self._blocked_actions(negative_constraints)
        path = resolved_path or self._workspace_from_targets(target_paths)
        for action in actions:
            permission = str(permission_aliases.get(action, action))
            if action in blocked_actions:
                decisions.append(
                    OperationPermissionDecision(
                        action=action,
                        canonical_action=action,
                        permission=permission,
                        decision="denied",
                        reason_code="negative_constraint_blocks_action",
                        requires_approval=False,
                        scope={"negative_constraints": negative_constraints},
                    )
                )
                continue
            matrix_decision = self.permission_matrix.decide(path=path, permission=permission)
            value = "ask" if matrix_decision.status == "approval_required" else matrix_decision.status
            decisions.append(
                OperationPermissionDecision(
                    action=action,
                    canonical_action=action,
                    permission=str(matrix_decision.permission),
                    decision=value,  # type: ignore[arg-type]
                    reason_code=matrix_decision.reason_code,
                    requires_approval=matrix_decision.status == "approval_required",
                    scope={
                        "workspace_id": matrix_decision.workspace_id,
                        "workspace_role": matrix_decision.workspace_role,
                        "root_path": matrix_decision.root_path,
                        "target_path": matrix_decision.target_path,
                    },
                )
            )
        return decisions

    def _blocked_actions(self, constraints: dict[str, bool]) -> set[str]:
        blocks = self.policy.get("constraint_blocks", {}) or {}
        blocked: set[str] = set()
        for name in constraints:
            for action in blocks.get(name, []) or []:
                blocked.add(str(action))
        return blocked

    def _workspace_from_targets(self, target_paths: list[str]) -> str | None:
        for item in target_paths:
            path = Path(item)
            if path.is_absolute():
                return str(path.parent if path.suffix else path)
        return None

    def _risk_level(self, actions: list[str]) -> str:
        if any(action.startswith("shell_") for action in actions):
            return "high"
        if any(action in {"create_file", "modify_file", "apply_patch", "artifact_create"} for action in actions):
            return "medium"
        return "low"

    def _normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().split())

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "operation_contract",
            "policy_path": str(self.policy_path),
            "action_aliases": sorted((self.policy.get("action_aliases", {}) or {}).keys()),
        }
