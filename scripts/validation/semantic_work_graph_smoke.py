from __future__ import annotations

import argparse
import json
from pathlib import Path

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_work_graph_interpreter_service import (
    SemanticWorkGraphInterpreterService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


class _PinnedModelRouter(ModelRouterService):
    def __init__(self, model_id: str) -> None:
        super().__init__()
        self.model_id = model_id

    def select_model(
        self,
        *,
        requested_model_id=None,
        purpose="chat",
        role_id="speaker",
    ):
        return super().select_model(
            requested_model_id=self.model_id,
            purpose=purpose,
            role_id=role_id,
        )


def _load_run(path: Path) -> TaskRun:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    return TaskRun.model_validate(raw)


def _graph_summary(graph) -> dict:
    authority = SemanticExecutionGraphAuthorityService()
    return {
        "semantic_graph_id": graph.semantic_graph_id,
        "status": graph.status,
        "authority_valid": authority.verify(graph),
        "work_unit_count": len(graph.work_units),
        "edge_count": len(graph.edges),
        "reason_codes": list(graph.reason_codes),
        "work_units": [
            {
                "work_unit_id": unit.work_unit_id,
                "source_step_ids": list(unit.source_step_ids),
                "semantic_goal": unit.semantic_goal,
                "work_modes": list(unit.work_modes),
                "classification_status": unit.classification_status,
                "required_capabilities": list(unit.required_capabilities),
                "requested_effects": list(unit.requested_effects),
                "prohibited_effects": list(unit.prohibited_effects),
                "contains_side_effect": unit.contains_side_effect,
            }
            for unit in graph.work_units
        ],
        "edges": [
            {
                "producer_work_unit_id": edge.producer_work_unit_id,
                "consumer_work_unit_id": edge.consumer_work_unit_id,
                "relation": edge.relation,
                "required": edge.required,
                "source_refs": list(edge.source_refs),
            }
            for edge in graph.edges
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--output")
    args = parser.parse_args()

    run = _load_run(Path(args.run_json))
    vocabulary_result = TaskSemanticVocabularyCompilerService().compile_for_run(
        run=run
    )
    if (
        vocabulary_result.status != "compiled"
        or vocabulary_result.vocabulary is None
    ):
        report = {
            "model_id": args.model_id,
            "source_run_id": run.run_id,
            "semantic_status": "insufficient_evidence",
            "reason_code": "TASK_SEMANTIC_VOCABULARY_SMOKE_COMPILATION_FAILED",
            "vocabulary_reason_codes": vocabulary_result.reason_codes,
            "deterministic_gate_safety_pass": False,
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        print(rendered)
        return 2

    run.plan.task_semantic_vocabulary = vocabulary_result.vocabulary

    router = _PinnedModelRouter(args.model_id)
    reasoner = ContractBoundSemanticReasoner(
        router=router,
        invocation=ModelInvocationService(router=router),
        timeout_seconds=args.timeout_seconds,
    )
    service = SemanticWorkGraphInterpreterService(reasoner=reasoner)
    result = service.interpret_for_run(run=run)
    provenance = dict(result.provenance or {})
    real_inference = provenance.get("real_inference")
    status = str(result.status or "")
    graph = result.graph

    safety_pass = (
        real_inference is True
        and status in {"accepted", "insufficient_evidence"}
        and (
            graph is None
            or SemanticExecutionGraphAuthorityService().verify(graph)
        )
    )
    report = {
        "model_id": args.model_id,
        "source_run_id": run.run_id,
        "real_inference": real_inference,
        "semantic_status": status,
        "reason_code": result.reason_code,
        "semantic_acceptance": status == "accepted",
        "deterministic_gate_safety_pass": safety_pass,
        "provenance": provenance,
        "candidate": dict(result.candidate or {}),
        "graph": _graph_summary(graph) if graph is not None else None,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if safety_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
