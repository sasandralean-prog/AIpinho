from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.schemas.interaction.contracts import ChatMessageCreateRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService
from aipinho.services.events.event_core import EventPublisherService
from aipinho.services.interaction.interaction_core import (
    ChatMessageService,
    ChatSessionService,
)


class TaskRunChatResultPublisherService:
    def __init__(
        self,
        *,
        session_service: ChatSessionService | None = None,
        message_service: ChatMessageService | None = None,
        result_index: ChatResultIndexService | None = None,
        event_publisher: EventPublisherService | None = None,
    ) -> None:
        self.session_service = session_service or ChatSessionService()
        self.message_service = message_service or ChatMessageService()
        self.result_index = result_index or ChatResultIndexService()
        self.event_publisher = event_publisher or EventPublisherService()

    def publish(self, run: TaskRun, result: TaskRunResult | None) -> dict[str, Any]:
        session_id = run.session_id
        if result is None:
            return {"status": "skipped", "reason": "task_result_missing"}
        if not session_id or self.session_service.get(session_id) is None:
            return {"status": "skipped", "reason": "persistent_chat_session_not_found"}
        if not result.safe_to_display:
            return {"status": "skipped", "reason": "task_result_not_safe_to_display"}

        existing = self._existing_message(session_id, run.run_id)
        if existing is not None:
            return {
                "status": "already_published",
                "message_id": existing.message_id,
                "task_id": run.task_id,
                "task_run_id": run.run_id,
            }

        message_type = (
            "assistant_final_answer"
            if result.status == "completed"
            else "assistant_degraded_answer"
        )
        response_status = "ok" if result.status == "completed" else "degraded"
        operation_type = str(
            run.intent_map.get("intent_type")
            or run.contract_type
            or "task_run"
        )
        evidence_refs = self._evidence_refs(run, result)
        content = self._render_message(result)
        source_event_id = self._publish_event(run, result, session_id)
        metadata = {
            "source": "task_run_result_publisher",
            "chat_response_status": response_status,
            "status": result.status,
            "operational_session_id": session_id,
            "task_run_id": run.run_id,
            "intent_type": operation_type,
            "requires_task": "True",
            "approval_required": "False",
            "rag_used": "False",
            "memory_used": "False",
            "fallback_used": "False",
            "real_inference": "False",
            "message_type": message_type,
            "operation_type": operation_type,
            "operation_id": run.run_id,
            "requires_user_action": "False",
            "is_final_answer": str(result.status == "completed"),
            "grounded": "True",
            "grounding_required": "False",
            "raw_available": "False",
            "validation_status": str(
                (result.validation or {}).get("status") or "not_available"
            ),
            "evidence_refs": evidence_refs,
        }
        message = self.message_service.create(
            session_id,
            ChatMessageCreateRequest(
                role="assistant",
                content=content,
                source_event_id=source_event_id,
                task_id=run.task_id,
                metadata=metadata,
            ),
        )

        result_ref_id = None
        if result.status == "completed":
            response = ChatResponse(
                response_id=f"task_result_{run.run_id}",
                session_id=session_id,
                task_id=run.task_id,
                result_ref_id=run.run_id,
                operation_id=run.run_id,
                operation_type=operation_type,
                message_type="assistant_final_answer",
                status="ok",
                message=content,
                intent={
                    "intent_type": operation_type,
                    "requires_task": True,
                    "result_kind": "summary",
                },
                policy={"approval_required_for": []},
                evidence_refs=evidence_refs,
                requires_user_action=False,
                is_final_answer=True,
                grounded=True,
            )
            result_ref_id = self.result_index.add_final_answer(
                session_id,
                response,
                message.message_id,
            )
        return {
            "status": "published",
            "message_id": message.message_id,
            "task_id": run.task_id,
            "task_run_id": run.run_id,
            "result_ref_id": result_ref_id,
        }

    def _existing_message(self, session_id: str, run_id: str):
        for message in reversed(self.message_service.list(session_id=session_id, limit=500)):
            if (
                message.role == "assistant"
                and str(message.metadata.get("task_run_id") or "") == run_id
            ):
                return message
        return None

    def _render_message(self, result: TaskRunResult) -> str:
        report = result.outputs.get("project_report")
        if isinstance(report, dict):
            rendered = str(report.get("rendered_markdown") or "").strip()
            if rendered:
                return rendered
        parts = [result.summary.strip()]
        if result.limitations:
            parts.append("Limitações:\n- " + "\n- ".join(result.limitations))
        if result.blocked_items:
            parts.append("Itens bloqueados:\n- " + "\n- ".join(result.blocked_items))
        if result.warnings:
            parts.append("Avisos:\n- " + "\n- ".join(result.warnings))
        return "\n\n".join(part for part in parts if part)

    def _evidence_refs(
        self,
        run: TaskRun,
        result: TaskRunResult,
    ) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = [
            {
                "type": "task_run",
                "ref_id": run.run_id,
                "human_label": "TaskRun supervisionada",
            }
        ]
        validation_id = (result.validation or {}).get("validation_id")
        if validation_id:
            refs.append(
                {
                    "type": "validation",
                    "ref_id": str(validation_id),
                    "human_label": "Validação da TaskRun",
                }
            )
        report = result.outputs.get("project_report")
        if isinstance(report, dict) and report.get("report_id"):
            refs.append(
                {
                    "type": "report",
                    "ref_id": str(report["report_id"]),
                    "human_label": "Relatório da análise",
                }
            )
        return refs

    def _publish_event(
        self,
        run: TaskRun,
        result: TaskRunResult,
        session_id: str,
    ) -> str | None:
        try:
            event = self.event_publisher.publish(
                EventPublishRequest(
                    event_type="task_result_published_to_chat",
                    source_service="task_runtime",
                    human_summary="Resultado terminal da task publicado na conversa de origem.",
                    status=result.status,
                    correlation_id=run.run_id,
                    payload={
                        "session_id": session_id,
                        "task_id": run.task_id or run.run_id,
                        "task_run_id": run.run_id,
                        "result_status": result.status,
                        "validation_status": (result.validation or {}).get("status"),
                    },
                )
            )
            return event.event_id
        except Exception:
            return None
