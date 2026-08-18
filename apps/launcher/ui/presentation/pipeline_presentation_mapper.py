from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.launcher.ui.utils.formatting import as_text
from apps.launcher.ui.utils.redaction import redact


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"none", "null", "unknown"} else text


def _metadata(card: dict[str, Any]) -> dict[str, Any]:
    value = card.get("metadata")
    return value if isinstance(value, dict) else {}


def _answers(card: dict[str, Any]) -> dict[str, Any]:
    value = card.get("answers")
    return value if isinstance(value, dict) else {}


def _answer_text(card: dict[str, Any], key: str) -> str:
    value = _answers(card).get(key)
    if isinstance(value, dict):
        return _clean(value.get("reason") or value.get("answer"))
    if isinstance(value, list):
        return ", ".join(_clean(item) for item in value if _clean(item))
    return _clean(value)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class PipelineApprovalPresentation:
    approval_id: str
    status: str
    title: str
    summary: str
    task_id: str | None = None
    operation: str = "unknown"
    risk: str = "unknown"
    approval_kind: str | None = None
    linked_task_run_id: str | None = None
    details: str = ""

    @property
    def linked_to_task(self) -> bool:
        return bool(self.linked_task_run_id or self.task_id)


@dataclass(frozen=True)
class PipelineTaskPresentation:
    task_id: str | None
    title: str
    summary: str
    status: str
    approval_id: str | None = None
    approval_kind: str | None = None
    linked_task_run_id: str | None = None
    details: str = ""
    queue_total: int = 0
    queue_requires_decision: int = 0
    task_approvals_pending: int = 0
    standalone_approvals_pending: int = 0

    @property
    def can_approve(self) -> bool:
        return bool(self.approval_id)


class PipelinePresentationMapper:
    def mobile_task(self, payload: dict[str, Any]) -> PipelineTaskPresentation:
        queue = payload.get("queue") if isinstance(payload.get("queue"), dict) else {}
        cards = self.mobile_cards(payload)
        task_card = self._find_card(cards, "task_state")
        approval = self.mobile_selected_approval(payload)
        task_id = _clean(payload.get("selected_task_id") or payload.get("task_id") or queue.get("selected_task_id")) or None
        state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
        status = _clean(state.get("status")) or _clean(task_card.get("status")) or "unknown"
        happening = _answer_text(task_card, "what_is_happening")
        why = _answer_text(task_card, "why_is_it_happening")
        summary = happening or _clean(state.get("human_summary")) or "Fila de tasks carregada pelo view-model mobile."
        if why:
            summary = "\n".join([summary, why])
        return PipelineTaskPresentation(
            task_id=task_id,
            title=f"Task {task_id}" if task_id else "Fila de tasks",
            summary=summary,
            status=status,
            approval_id=approval.approval_id if approval else None,
            approval_kind=approval.approval_kind if approval else (_clean(payload.get("approval_kind") or queue.get("approval_kind")) or None),
            linked_task_run_id=approval.linked_task_run_id if approval else (_clean(payload.get("linked_task_run_id") or queue.get("linked_task_run_id")) or None),
            details=redact(as_text(payload)),
            queue_total=_int_value(queue.get("total")),
            queue_requires_decision=_int_value(queue.get("requires_decision")),
            task_approvals_pending=_int_value(payload.get("task_approvals_pending") or queue.get("task_approvals_pending")),
            standalone_approvals_pending=_int_value(payload.get("standalone_approvals_pending") or queue.get("standalone_approvals_pending")),
        )

    def mobile_selected_approval(self, payload: dict[str, Any]) -> PipelineApprovalPresentation | None:
        approval_card = self._find_card(self.mobile_cards(payload), "approval")
        metadata = _metadata(approval_card)
        queue = payload.get("queue") if isinstance(payload.get("queue"), dict) else {}
        approval_id = _clean(payload.get("selected_approval_id") or queue.get("selected_approval_id") or metadata.get("approval_id"))
        if not approval_id:
            return None
        status = _clean(metadata.get("approval_status") or approval_card.get("status")) or "pending"
        actions = metadata.get("actions_requested")
        action_text = ", ".join(str(item).replace("_", " ") for item in actions) if isinstance(actions, list) else _clean(actions)
        happening = _answer_text(approval_card, "what_is_happening") or "Existe um pedido de approval pendente."
        why = _answer_text(approval_card, "why_is_it_happening")
        parts = [happening]
        if action_text:
            parts.append(f"Acoes solicitadas: {action_text}.")
        if why:
            parts.append(why)
        task_id = _clean(payload.get("selected_task_id") or payload.get("task_id") or queue.get("selected_task_id")) or None
        linked_task_run_id = _clean(payload.get("linked_task_run_id") or queue.get("linked_task_run_id") or metadata.get("linked_task_run_id")) or None
        approval_kind = _clean(payload.get("approval_kind") or queue.get("approval_kind") or metadata.get("approval_kind")) or None
        return PipelineApprovalPresentation(
            approval_id=approval_id,
            status=status,
            title=f"Approval {approval_id}",
            summary="\n".join(parts),
            task_id=task_id if linked_task_run_id else None,
            operation=_clean(metadata.get("operation_type")) or approval_kind or "unknown",
            risk=_clean(metadata.get("risk_level")) or "unknown",
            approval_kind=approval_kind,
            linked_task_run_id=linked_task_run_id,
            details=redact(as_text(approval_card)),
        )

    def standalone_approvals(self, approvals_payload: dict[str, Any]) -> list[PipelineApprovalPresentation]:
        approvals = approvals_payload.get("approvals") if isinstance(approvals_payload.get("approvals"), list) else []
        rows: list[PipelineApprovalPresentation] = []
        for approval in approvals:
            if not isinstance(approval, dict):
                continue
            approval_id = _clean(approval.get("approval_id"))
            if not approval_id:
                continue
            task_id = _clean(approval.get("task_id") or approval.get("run_id")) or None
            if task_id:
                continue
            operation = _clean(approval.get("operation_type")) or _clean(approval.get("approval_scope")) or "unknown"
            risk = _clean(approval.get("risk_level")) or "unknown"
            workspace = _clean(approval.get("workspace_path") or approval.get("workspace_id")) or "-"
            summary = f"Operacao: {operation}. Risco: {risk}. Workspace: {workspace}."
            rows.append(PipelineApprovalPresentation(
                approval_id=approval_id,
                status=_clean(approval.get("status")) or "pending",
                title=f"Approval avulso {approval_id}",
                summary=summary,
                task_id=None,
                operation=operation,
                risk=risk,
                approval_kind=_clean(approval.get("approval_scope")) or "standalone_approval",
                linked_task_run_id=None,
                details=redact(as_text(approval)),
            ))
        return rows

    def mobile_cards(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        cards = payload.get("cards")
        return [card for card in cards if isinstance(card, dict)] if isinstance(cards, list) else []

    def card_summary(self, card: dict[str, Any]) -> str:
        happening = _answer_text(card, "what_is_happening")
        why = _answer_text(card, "why_is_it_happening")
        safety = _answer_text(card, "is_it_safe")
        actions = _answer_text(card, "what_can_i_do_now")
        parts = [item for item in (happening, why, f"Seguranca: {safety}" if safety else "", f"Acoes: {actions}" if actions else "") if item]
        return "\n".join(parts) or _clean(card.get("title")) or "Card sem resumo."

    def tasks(self, payload: dict[str, Any]) -> list[PipelineTaskPresentation]:
        raw_cards = payload.get("cards") if isinstance(payload.get("cards"), list) else []
        return [self._legacy_task(card) for card in raw_cards if isinstance(card, dict)]

    def _legacy_task(self, card: dict[str, Any]) -> PipelineTaskPresentation:
        task_id = _clean(card.get("task_id") or card.get("id"))
        status = _clean(card.get("status") or card.get("state")) or "unknown"
        summary = _clean(card.get("summary") or card.get("human_summary") or card.get("title")) or "Task registrada pelo backend."
        approval_id = self._approval_id(card)
        return PipelineTaskPresentation(
            task_id=task_id or None,
            title=f"Task {task_id or 'sem id'}",
            summary=summary,
            status=status,
            approval_id=approval_id,
            details=redact(as_text(card)),
        )

    def _approval_id(self, card: dict[str, Any]) -> str | None:
        for key in ("approval_id", "active_approval_id", "pending_approval_id"):
            value = _clean(card.get(key))
            if value:
                return value
        approvals = card.get("approvals")
        if isinstance(approvals, list):
            for approval in approvals:
                if isinstance(approval, dict):
                    value = _clean(approval.get("approval_id") or approval.get("id"))
                    if value:
                        return value
        return None

    @staticmethod
    def _find_card(cards: list[dict[str, Any]], card_type: str) -> dict[str, Any]:
        return next((card for card in cards if _clean(card.get("card_type")) == card_type), {})
