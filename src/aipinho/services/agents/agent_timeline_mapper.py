from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import AgentEvent, AgentTimelineItem
from aipinho.services.events.event_core import redact_payload


TITLE_BY_EVENT_TYPE = {
    "agent_run_created": "Run criado",
    "agent_run_started": "Execucao iniciada",
    "agent_run_planning": "Planejamento em andamento",
    "agent_run_waiting": "Run aguardando",
    "agent_run_running": "Run em execucao",
    "agent_run_completed": "Run concluido",
    "agent_run_completed_with_warnings": "Run concluido com avisos",
    "agent_run_failed": "Run falhou",
    "agent_run_blocked": "Run bloqueado",
    "agent_run_cancelled": "Run cancelado",
    "agent_explanation": "Explicacao",
    "agent_plan_summary": "Resumo do plano",
    "agent_next_action": "Proxima acao",
    "agent_status_update": "Atualizacao de status",
    "agent_warning": "Aviso",
    "agent_error": "Erro",
    "policy_check_started": "Checagem de politica iniciada",
    "policy_check_completed": "Checagem de politica concluida",
    "approval_required": "Aprovacao necessaria",
    "approval_granted": "Aprovacao concedida",
    "approval_denied": "Aprovacao negada",
    "auto_approval_granted": "Autoaprovacao concedida",
    "auto_approval_denied": "Autoaprovacao negada",
    "preview_created": "Preview criado",
    "apply_started": "Aplicacao iniciada",
    "apply_finished": "Aplicacao finalizada",
    "validation_started": "Validacao iniciada",
    "validation_step": "Etapa de validacao",
    "validation_passed": "Validacao passou",
    "validation_failed": "Validacao falhou",
    "shell_stdout": "Saida do shell",
    "shell_stderr": "Erro do shell",
    "artifact_created": "Artifact criado",
    "artifact_download_ready": "Download pronto",
    "report_created": "Relatorio criado",
}


class AgentEventTimelineMapper:
    def __init__(self, visual_limit: int = 2000) -> None:
        self.visual_limit = visual_limit

    def map_event(self, event: AgentEvent, *, mode: str = "normal") -> AgentTimelineItem:
        title = TITLE_BY_EVENT_TYPE.get(event.event_type, event.event_type.replace("_", " ").title())
        full_body = str(redact_payload(event.human_message or event.technical_summary_sanitized or ""))
        body = self._limit(full_body)
        details: dict[str, Any] = {}
        if mode in {"details", "raw"}:
            details = {
                "event_type": event.event_type,
                "run_id": event.run_id,
                "sequence": event.sequence,
                "session_sequence": event.session_sequence,
                "status": event.status,
                "severity": event.severity,
                "evidence_refs": event.evidence_refs,
                "approval_id": event.approval_id,
                "validation_id": event.validation_id,
                "artifact_ids": event.artifact_ids,
                "progress_current": event.progress_current,
                "progress_total": event.progress_total,
                "metadata": redact_payload(event.payload_sanitized),
            }
        return AgentTimelineItem(
            event_id=event.event_id,
            run_id=event.run_id,
            session_id=event.session_id,
            agent_id=event.agent_id,
            sequence=event.sequence,
            session_sequence=event.session_sequence,
            event_type=event.event_type,
            title=title,
            body=body,
            severity=event.severity,
            status=event.status,
            created_at=event.created_at,
            copy_text=self._copy_text(title, full_body, event),
            raw_available=bool(event.raw_ref),
            details=details,
        )

    def map_events(self, events: list[AgentEvent], *, mode: str = "normal") -> list[AgentTimelineItem]:
        return [self.map_event(event, mode=mode) for event in events]

    def _limit(self, value: str) -> str:
        if len(value) <= self.visual_limit:
            return value
        return value[: self.visual_limit] + f"...[truncated {len(value) - self.visual_limit} chars]"

    def _copy_text(self, title: str, body: str, event: AgentEvent) -> str:
        lines = [
            f"[{event.agent_id}] {title}",
            f"Run: {event.run_id}",
            f"Status: {event.status}",
            f"Severity: {event.severity}",
            body,
        ]
        return "\n".join(line for line in lines if line)
