from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.chat.chat_response import ChatPolicyBlock, ChatResponse


class BlockedPolicyResponseService:
    """Builds traceable policy-block responses without requiring a TaskRun."""

    def build(
        self,
        *,
        session_id: str | None,
        operation_id: str,
        operation_type: str,
        policy_name: str,
        block_reason_code: str,
        human_reason: str,
        safe_alternatives: list[str],
        task_id: str | None = None,
        requested_capability: str | None = None,
        requested_action: str | None = None,
        workspace_id: str | None = None,
        workspace_role: str | None = None,
        policy_decision_id: str | None = None,
        evidence_refs: list[dict[str, object]] | None = None,
        requires_user_action: bool = False,
        warnings: list[str] | None = None,
        blocked_stage: str | None = None,
        technical_reason_sanitized: str | None = None,
        source_read_status: str | None = None,
        artifact_output_status: str | None = None,
        approval_status: str | None = None,
        validation_status: str | None = None,
        validation_id: str | None = None,
        trace_id: str | None = None,
        event_id: str | None = None,
    ) -> ChatResponse:
        block_id = f"block_{uuid4().hex}"
        trace_id = trace_id or f"trace_{uuid4().hex}"
        event_id = event_id or f"event_{uuid4().hex}"
        evidence = [dict(item) for item in evidence_refs or []]
        alternatives = [item for item in safe_alternatives if item.strip()]
        alternative_text = alternatives[0] if alternatives else "Revise o pedido ou consulte os detalhes da policy."
        policy_block = ChatPolicyBlock(
            block_id=block_id,
            operation_id=operation_id,
            session_id=session_id,
            task_id=task_id,
            operation_type=operation_type,
            requested_capability=requested_capability,
            requested_action=requested_action,
            workspace_id=workspace_id,
            workspace_role=workspace_role,
            policy_name=policy_name,
            policy_decision_id=policy_decision_id,
            block_reason_code=block_reason_code,
            human_reason=human_reason,
            safe_alternatives=alternatives,
            evidence_refs=evidence,
            trace_id=trace_id,
            event_id=event_id,
            requires_user_action=requires_user_action,
            blocked_stage=blocked_stage,
            technical_reason_sanitized=technical_reason_sanitized,
            source_read_status=source_read_status,
            artifact_output_status=artifact_output_status,
            approval_status=approval_status,
            validation_status=validation_status,
            validation_id=validation_id,
        )
        return ChatResponse(
            response_id=operation_id,
            session_id=session_id,
            task_id=task_id,
            status="blocked",
            message=(
                "Bloqueei esta acao por seguranca.\n"
                f"Motivo: {human_reason}\n"
                f"Alternativa segura: {alternative_text}"
            ),
            intent={
                "intent_type": operation_type,
                "requires_task": task_id is not None,
                "requires_workspace": workspace_id is not None,
            },
            policy={
                "status": "blocked",
                "policy_name": policy_name,
                "policy_decision_id": policy_decision_id,
                "block_reason_code": block_reason_code,
                "requested_capability": requested_capability,
                "requested_action": requested_action,
                "workspace_id": workspace_id,
                "workspace_role": workspace_role,
                "safe_alternatives": alternatives,
                "blocked_stage": blocked_stage,
                "source_read_status": source_read_status,
                "artifact_output_status": artifact_output_status,
                "approval_status": approval_status,
                "validation_status": validation_status,
                "validation_id": validation_id,
                "approval_required_for": [],
            },
            warnings=list(dict.fromkeys([block_reason_code, *(warnings or [])])),
            message_type="blocked_policy_message",
            operation_type=operation_type,
            operation_id=operation_id,
            evidence_refs=evidence,
            requires_user_action=requires_user_action,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            grounding_missing_reason=block_reason_code,
            policy_block=policy_block,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "blocked_policy_response"}
