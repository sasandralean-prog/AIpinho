from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExternalSpeakerTruthAudit:
    status: str
    decision: str
    allowed_actions: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    reason_code: str = "ok"


class ExternalSpeakerTruthAuditor:
    """Validate external adapter output as an audit signal, not a final answer.

    External models may approve, reject, request another execution, or report
    inconsistencies. They cannot replace AIpinho's final answer or improve it
    into a new narrative after AIpinho has spoken.
    """

    ALLOWED_ACTIONS = [
        "validate",
        "approve",
        "reject",
        "request_new_execution",
        "detect_inconsistency",
    ]
    APPROVE_RE = re.compile(r"\b(aprov|approve|approved|pronto|ready|passou|ok)\b", re.IGNORECASE)
    REJECT_RE = re.compile(r"\b(rejeit|negad|reject|denied|falhou|failed|erro|error|bloque|blocked)\b", re.IGNORECASE)
    RETRY_RE = re.compile(r"\b(reexecut|nova execu|retry|rerun|tente novamente|corrigir|fix)\b", re.IGNORECASE)
    INCONSISTENCY_RE = re.compile(r"\b(inconsist|diverg|contradi|missing|falt|sem evid|needs evidence)\b", re.IGNORECASE)
    REWRITE_RE = re.compile(
        r"\b(reescrev|reescrito|resumindo|em resumo|vers\S* melhorada|vers\S* final|"
        r"resposta final|melhorei|completei|reorganizei|corrigi a resposta|final answer)\b",
        re.IGNORECASE,
    )

    def audit(self, text: str) -> ExternalSpeakerTruthAudit:
        clean = " ".join(str(text or "").replace("\r", "\n").split())
        violations: list[str] = []
        if self.REWRITE_RE.search(clean):
            violations.append("external_rewrite_or_summary_forbidden")
        allowed_actions: list[str] = ["validate"]
        decision = "validate"
        if self.INCONSISTENCY_RE.search(clean):
            allowed_actions.append("detect_inconsistency")
            decision = "detect_inconsistency"
        if self.RETRY_RE.search(clean):
            allowed_actions.append("request_new_execution")
            decision = "request_new_execution"
        if self.REJECT_RE.search(clean):
            allowed_actions.append("reject")
            decision = "reject"
        elif self.APPROVE_RE.search(clean):
            allowed_actions.append("approve")
            decision = "approve"
        if decision == "validate" and not violations:
            violations.append("auditor_decision_missing")
        status = "accepted" if not violations else "review_loop_required"
        return ExternalSpeakerTruthAudit(
            status=status,
            decision=decision,
            allowed_actions=list(dict.fromkeys(action for action in allowed_actions if action in self.ALLOWED_ACTIONS)),
            violations=violations,
            reason_code="ok" if not violations else "speaker_truth_auditor_rejected_external_output",
        )

    @staticmethod
    def human_summary(audit: ExternalSpeakerTruthAudit) -> str:
        if audit.status == "accepted":
            return f"Auditor externo: {audit.decision}. AIpinho permanece como Speaker Truth Authority."
        return (
            "Auditor externo exige review loop; output externo nao pode substituir, "
            "reescrever ou completar a resposta da AIpinho."
        )
