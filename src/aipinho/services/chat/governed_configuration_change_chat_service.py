from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision


class GovernedConfigurationChangeChatService:
    """Builds a governed preview for prompt-requested policy/config changes.

    The service does not mutate configuration files. It turns a natural language
    request into an auditable preview that can later be promoted through the
    normal task/approval/validation flow.
    """

    def preview(self, *, session_id: str, decision: ChatOperationDecision, prompt: str) -> ChatResponse:
        targets = self._targets(decision.metadata)
        scope = self._scope(targets)
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="preview",
            message=(
                "Entendi que voce quer alterar configuracoes governadas da AIpinho. "
                "Isso pode ser preparado como preview, mas nao sera aplicado diretamente pelo chat. "
                "Para prosseguir, a mudanca precisa virar task governada com diff/preview, approval e validacao."
            ),
            intent={
                "intent_type": "governed_configuration_change",
                "requires_task": True,
                "requires_workspace": False,
                "targets": targets,
            },
            policy={
                "governed_configuration_change": True,
                "direct_mutation_allowed": False,
                "requires_preview": True,
                "requires_approval": True,
                "requires_validation": True,
                "scope": scope,
            },
            contract_preview={
                "operation_type": "governed_configuration_change",
                "requested_targets": targets,
                "requested_change_summary": prompt.strip(),
                "required_flow": ["task_contract", "diff_preview", "approval", "validation", "audit_event"],
                "forbidden_shortcuts": ["direct_yaml_write_from_chat", "blanket_permission", "policy_bypass"],
            },
            operation_id=decision.operation_id,
            operation_type="governed_configuration_change",
            message_type="task_preview",
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            evidence_refs=[{"type": "routing_policy", "ref_id": "chat_operation_routing_policy"}],
            next_actions=[
                ChatNextAction(
                    type="create_governed_task",
                    label="Criar preview governado",
                    target_id=decision.operation_id,
                )
            ],
            warnings=["configuration_change_requires_governed_preview"],
        )

    @staticmethod
    def _targets(metadata: dict[str, Any]) -> list[str]:
        targets = metadata.get("configuration_targets")
        if isinstance(targets, list):
            return [str(item) for item in targets if str(item).strip()]
        return ["config"]

    @staticmethod
    def _scope(targets: list[str]) -> str:
        return "multiple" if len(targets) > 1 else targets[0]
