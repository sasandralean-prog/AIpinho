from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import CanonicalExecutionPlan, CanonicalExecutionStep
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.semantics.contract_bound_semantic_reasoner import ContractBoundSemanticReasoner
from aipinho.services.semantics.semantic_demand_interpreter_service import SemanticDemandInterpreterService
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


class _PinnedModelRouter(ModelRouterService):
    def __init__(self, model_id: str) -> None:
        super().__init__()
        self.model_id = model_id

    def select_model(self, *, requested_model_id=None, purpose='chat', role_id='speaker'):
        return super().select_model(
            requested_model_id=self.model_id,
            purpose=purpose,
            role_id=role_id,
        )


def _payload() -> dict:
    return {
        'semantic_goal': 'analyze implementation behavior and produce a readonly report',
        'operation_kind': 'workspace_analysis_readonly',
        'intent_map': {
            'operation_type': 'readonly_analysis',
            'requested_deliverables': ['analysis report'],
        },
        'targets': ['workspace'],
        'artifact_expectations': ['analysis.md'],
        'validation_requirements': ['output_validation'],
        'required_capabilities': ['read_workspace'],
        'requested_deliverables': ['analysis report'],
        'policy_snapshot': {},
        'semantic_intent_graph': {
            'knowledge_output': True,
            'observational_intent': True,
            'readonly_contract': True,
            'mutation_intent': False,
            'execution_intent': False,
        },
        'steps': [
            {
                'step_id': 'step1',
                'action': 'project_analysis',
                'side_effect': False,
                'required_capabilities': ['read_workspace'],
            }
        ],
    }


def _vocabulary(payload: dict):
    step = CanonicalExecutionStep(
        step_id="step1",
        step_type="analysis",
        action="project_analysis",
        side_effect=False,
        required_capabilities=["read_workspace"],
    )
    canonical = CanonicalExecutionPlan(
        semantic_goal=payload["semantic_goal"],
        operation_kind=payload["operation_kind"],
        execution_steps=[step],
        required_capabilities=["read_workspace"],
        rollback_strategy={},
        trace_id="trace_semantic_smoke",
        metadata={
            "semantic_intent_graph": payload["semantic_intent_graph"],
            "requested_deliverables": payload["requested_deliverables"],
        },
    )
    plan = TaskRunPlan(
        plan_id="plan_semantic_smoke",
        contract_type="readonly_analysis",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_semantic_smoke",
        task_id="task_semantic_smoke",
        plan=plan,
        intent_map=payload["intent_map"],
        capabilities_required=["read_workspace"],
    )
    compilation = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    if compilation.status != "compiled" or compilation.vocabulary is None:
        raise RuntimeError(
            "task_semantic_vocabulary_smoke_compilation_failed:"
            + ",".join(compilation.reason_codes)
        )
    return compilation.vocabulary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=120)
    parser.add_argument('--output')
    args = parser.parse_args()

    router = _PinnedModelRouter(args.model_id)
    reasoner = ContractBoundSemanticReasoner(
        router=router,
        invocation=ModelInvocationService(router=router),
        timeout_seconds=args.timeout_seconds,
    )
    service = SemanticDemandInterpreterService(reasoner=reasoner)
    payload = _payload()
    vocabulary = _vocabulary(payload)
    result = service.interpret(
        source_payload=payload,
        semantic_graph=payload['semantic_intent_graph'],
        vocabulary=vocabulary,
    )
    provenance = dict(result.get('provenance') or {})
    real_inference = provenance.get('real_inference')
    status = str(result.get('status') or '')
    safety_pass = real_inference is True and status in {'accepted', 'insufficient_evidence'}
    report = {
        'model_id': args.model_id,
        'real_inference': real_inference,
        'semantic_status': status,
        'reason_code': result.get('reason_code'),
        'semantic_acceptance': status == 'accepted',
        'deterministic_gate_safety_pass': safety_pass,
        'result': result,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding='utf-8')
    print(rendered)
    return 0 if safety_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
