from __future__ import annotations

from typing import Iterable

from aipinho.schemas.memory.operational_memory import OperationalMemoryRecord
from aipinho.schemas.runtime.evidence_engine import (
    DecisionAudit,
    EvidenceBackedDecision,
    EvidenceIndex,
    EvidenceItem,
    EvidenceReasoning,
    EvidenceScore,
)
from aipinho.schemas.runtime.task_run import TaskRun


class EvidenceCollector:
    def collect_from_task_run(
        self,
        run: TaskRun,
        *,
        operational_memory: Iterable[OperationalMemoryRecord] | None = None,
    ) -> list[EvidenceItem]:
        evidence = [
            EvidenceItem(
                kind="task_run",
                source_id=run.run_id,
                source_ref=run.run_id,
                summary=f"TaskRun status {run.status}.",
                strength="strong",
                metadata_sanitized={
                    "status": run.status,
                    "contract_type": run.contract_type,
                    "operation_type": run.operation_type,
                    "runtime_profile": run.runtime_profile,
                },
            ),
            EvidenceItem(
                kind="task_run_plan",
                source_id=run.plan.plan_id,
                source_ref=run.run_id,
                summary=f"TaskRunPlan status {run.plan.status} with {len(run.plan.steps)} steps.",
                strength="strong",
                metadata_sanitized={"steps": len(run.plan.steps), "plan_status": run.plan.status},
            ),
            EvidenceItem(
                kind="policy_snapshot",
                source_id=run.run_id,
                source_ref=run.run_id,
                summary="Policy snapshot attached to TaskRun.",
                strength="medium",
                metadata_sanitized=run.policy_snapshot,
            ),
        ]
        if run.execution_graph:
            evidence.append(
                EvidenceItem(
                    kind="execution_graph",
                    source_id=run.execution_graph.graph_id,
                    source_ref=run.run_id,
                    summary=f"ExecutionGraph status {run.execution_graph.status}.",
                    strength="strong",
                    metadata_sanitized={
                        "nodes": len(run.execution_graph.nodes),
                        "edges": len(run.execution_graph.edges),
                        "status": run.execution_graph.status,
                    },
                )
            )
            for node in run.execution_graph.nodes:
                evidence.append(
                    EvidenceItem(
                        kind="execution_node",
                        source_id=node.node_id,
                        source_ref=run.execution_graph.graph_id,
                        summary=f"Node {node.step_id} routed to {node.worker} with status {node.status}.",
                        strength="medium",
                        metadata_sanitized={
                            "step_id": node.step_id,
                            "worker": node.worker,
                            "status": node.status,
                            "action": node.action,
                        },
                    )
                )
        for memory in operational_memory or []:
            evidence.append(
                EvidenceItem(
                    kind="operational_memory",
                    source_id=memory.memory_id,
                    source_ref=memory.source_run_id,
                    summary=memory.summary,
                    strength="medium",
                    metadata_sanitized={
                        "memory_type": memory.memory_type,
                        "outcome": memory.outcome,
                        "status": memory.status,
                    },
                )
            )
        return evidence


class EvidenceIndexService:
    def build(self, evidence: list[EvidenceItem]) -> EvidenceIndex:
        by_kind: dict[str, list[str]] = {}
        for item in evidence:
            by_kind.setdefault(item.kind, []).append(item.evidence_id)
        return EvidenceIndex(evidence=evidence, by_kind=by_kind)


class EvidenceScoreService:
    def score(self, index: EvidenceIndex, *, required_kinds: list[str] | None = None) -> EvidenceScore:
        required = required_kinds or ["task_run", "task_run_plan"]
        present = set(index.by_kind)
        missing = [kind for kind in required if kind not in present]
        strong = sum(1 for item in index.evidence if item.strength == "strong")
        medium = sum(1 for item in index.evidence if item.strength == "medium")
        weak = sum(1 for item in index.evidence if item.strength == "weak")
        raw_score = min(1.0, (strong * 0.34) + (medium * 0.18) + (weak * 0.06))
        if missing:
            status = "insufficient"
            raw_score = min(raw_score, 0.49)
        elif raw_score >= 0.75:
            status = "sufficient"
        else:
            status = "partial"
        return EvidenceScore(
            status=status,
            score=round(raw_score, 3),
            evidence_count=len(index.evidence),
            strong_count=strong,
            medium_count=medium,
            weak_count=weak,
            missing_required_kinds=missing,
            warnings=["missing_required_evidence"] if missing else [],
        )


class EvidenceReasoner:
    def reason(self, index: EvidenceIndex, score: EvidenceScore, *, required_kinds: list[str] | None = None) -> EvidenceReasoning:
        required = required_kinds or ["task_run", "task_run_plan"]
        present = sorted(index.by_kind)
        missing = [kind for kind in required if kind not in index.by_kind]
        if score.status == "sufficient":
            summary = "Evidence is sufficient for an auditable decision."
        elif score.status == "partial":
            summary = "Evidence is partial; decision should remain cautious."
        else:
            summary = "Evidence is insufficient; decision must be blocked or downgraded."
        return EvidenceReasoning(
            status=score.status,
            summary=summary,
            required_kinds=required,
            present_kinds=present,
            missing_kinds=missing,
            evidence_ids=[item.evidence_id for item in index.evidence],
        )


class DecisionBuilder:
    def build(
        self,
        *,
        subject: str,
        decision: str,
        index: EvidenceIndex,
        score: EvidenceScore,
        reasoning: EvidenceReasoning,
    ) -> EvidenceBackedDecision:
        status = "accepted" if score.status == "sufficient" else "blocked"
        return EvidenceBackedDecision(
            subject=subject,
            decision=decision,
            status=status,
            evidence_index_id=index.index_id,
            evidence_score=score,
            reasoning=reasoning,
            evidence_ids=[item.evidence_id for item in index.evidence],
        )


class DecisionAuditService:
    def audit(self, decision: EvidenceBackedDecision) -> DecisionAudit:
        if decision.status == "accepted" and decision.evidence_score.status == "sufficient":
            return DecisionAudit(
                decision_id=decision.decision_id,
                status="passed",
                reason="decision_has_sufficient_evidence",
                evidence_score=decision.evidence_score.score,
                evidence_count=decision.evidence_score.evidence_count,
            )
        return DecisionAudit(
            decision_id=decision.decision_id,
            status="failed",
            reason="decision_missing_required_evidence",
            evidence_score=decision.evidence_score.score,
            evidence_count=decision.evidence_score.evidence_count,
            missing_required_kinds=list(decision.evidence_score.missing_required_kinds),
        )


class EvidenceEngineService:
    def __init__(
        self,
        collector: EvidenceCollector | None = None,
        indexer: EvidenceIndexService | None = None,
        scorer: EvidenceScoreService | None = None,
        reasoner: EvidenceReasoner | None = None,
        builder: DecisionBuilder | None = None,
        auditor: DecisionAuditService | None = None,
    ) -> None:
        self.collector = collector or EvidenceCollector()
        self.indexer = indexer or EvidenceIndexService()
        self.scorer = scorer or EvidenceScoreService()
        self.reasoner = reasoner or EvidenceReasoner()
        self.builder = builder or DecisionBuilder()
        self.auditor = auditor or DecisionAuditService()

    def decide_from_task_run(
        self,
        run: TaskRun,
        *,
        subject: str,
        decision: str,
        required_kinds: list[str] | None = None,
        operational_memory: Iterable[OperationalMemoryRecord] | None = None,
    ) -> tuple[EvidenceBackedDecision, DecisionAudit]:
        evidence = self.collector.collect_from_task_run(run, operational_memory=operational_memory)
        index = self.indexer.build(evidence)
        score = self.scorer.score(index, required_kinds=required_kinds)
        reasoning = self.reasoner.reason(index, score, required_kinds=required_kinds)
        backed_decision = self.builder.build(
            subject=subject,
            decision=decision,
            index=index,
            score=score,
            reasoning=reasoning,
        )
        audit = self.auditor.audit(backed_decision)
        return backed_decision, audit
