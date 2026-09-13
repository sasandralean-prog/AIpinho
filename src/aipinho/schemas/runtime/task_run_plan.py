from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.runtime.execution_plan import CandidatePlan, CanonicalExecutionPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.runtime.task_run_trace import TaskRunTraceItem
from aipinho.schemas.semantics.task_semantic_vocabulary import TaskSemanticVocabulary
from aipinho.schemas.semantics.semantic_execution_graph import SemanticExecutionGraph
from aipinho.schemas.semantics.edge_semantic_demand import EdgeSemanticDemand
from aipinho.schemas.semantics.semantic_offer import SemanticOffer
from aipinho.schemas.semantics.offer_demand_compatibility import (
    OfferDemandCompatibility,
)

class TaskRunPlan(AIpinhoModel):
    plan_id: str
    contract_type: str
    status: str = "ready"
    steps: list[TaskRunStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[TaskRunTraceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    candidate_plan: CandidatePlan | None = None
    canonical_execution_plan: CanonicalExecutionPlan | None = None
    task_semantic_vocabulary: TaskSemanticVocabulary | None = None
    semantic_execution_graph: SemanticExecutionGraph | None = None
    edge_semantic_demands: list[EdgeSemanticDemand] = Field(default_factory=list)
    semantic_offers: list[SemanticOffer] = Field(default_factory=list)
    offer_demand_compatibilities: list[OfferDemandCompatibility] = Field(
        default_factory=list
    )
