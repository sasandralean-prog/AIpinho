from __future__ import annotations

from pathlib import Path

from tests.support.runtime_fixtures import runtime_run

from aipinho.schemas.external_collaboration import (
    ContinuousCollaborationStartRequest,
    ExternalAdapterEvaluationRequest,
    SuccessContractCreateRequest,
    SuccessEvaluationCreateRequest,
)
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.external_collaboration_service import ExternalCollaborationService
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _service(tmp_path: Path, task_runtime_service) -> ExternalCollaborationService:
    return ExternalCollaborationService(
        store=ExternalCollaborationStore(root=tmp_path / "external_collaboration"),
        runtime=task_runtime_service,
        universal_sessions=UniversalTaskSessionService(
            store=task_runtime_service.store,
            approvals=task_runtime_service.approvals,
        ),
    )


def _stored_run(task_runtime_service, *, status: str = "created"):
    run = runtime_run(status=status)
    task_runtime_service.store.create_run(run)
    return run


def test_continuous_collaboration_session_created_with_success_runtime(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service)
    contract = service.create_success_contract(
        SuccessContractCreateRequest(
            objective="Build validado.",
            acceptance_criteria=["Task completed", "Validation safe"],
            completion_definition="AIpinho valida e Speaker Truth permite declarar sucesso.",
        )
    )

    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(
            provider="external_model",
            task_run_id=run.run_id,
            success_contract_id=contract.success_contract_id,
            maximum_iterations=2,
        )
    )

    assert session.session_id.startswith("ccr_session_")
    assert session.task_run_id == run.run_id
    assert session.success_runtime.goal == "Build validado."
    assert session.success_runtime.maximum_iterations == 2
    assert session.metadata["universal_task_session_source"] is True


def test_polling_observes_universal_task_session_events(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service)
    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(provider="external_model", task_run_id=run.run_id)
    )
    task_runtime_service.store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="event_run_created",
            run_id=run.run_id,
            sequence=1,
            type="run_created",
            status="created",
            message="created",
        ),
    )

    payload = service.poll_continuous_session(session.session_id)

    assert payload is not None
    assert payload.retry_strategy == "Continue"
    assert payload.relevant_events[0]["type"] == "run_created"
    assert payload.session.last_event_sequence == 1


def test_adapter_success_evaluation_records_human_and_machine_outputs(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service)
    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(provider="external_model", task_run_id=run.run_id)
    )

    payload = service.adapt_and_receive_success_evaluation(
        "gemini",
        session.session_id,
        ExternalAdapterEvaluationRequest(
            provider_output="A validacao terminou, mas falta revisar assets.",
            confidence=0.8,
        ),
    )

    assert payload["external_may_execute"] is False
    assert payload["adapter_output"]["human_output"]
    updated = service.get_continuous_session(session.session_id)
    assert updated is not None
    assert updated.review_iteration == 1
    assert updated.memory.human_outputs
    assert updated.memory.machine_outputs


def test_retry_strategy_respects_maximum_iterations(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service)
    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(provider="external_model", task_run_id=run.run_id, maximum_iterations=1)
    )

    payload = service.receive_success_evaluation(
        session.session_id,
        SuccessEvaluationCreateRequest(
            provider="external_model",
            status="submitted",
            acceptance_score=0.3,
            blocking_findings=["Build failed"],
            needs_retry=True,
            confidence=0.9,
        ),
    )

    assert payload is not None
    assert payload["retry_strategy"] == "Needs Human"
    assert payload["session"]["review_iteration"] == 1
    assert payload["session"]["retry_state"]["reason"] == "maximum_iterations_reached"


def test_completion_depends_on_aipinho_validation_and_speaker_truth(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service, status="completed")
    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(provider="external_model", task_run_id=run.run_id, maximum_iterations=3)
    )

    not_done = service.receive_success_evaluation(
        session.session_id,
        SuccessEvaluationCreateRequest(
            provider="external_model",
            ready=True,
            acceptance_score=0.95,
            confidence=0.9,
            next_action="aipinho_decides",
        ),
    )

    assert not_done is not None
    assert not_done["retry_strategy"] == "Continue"
    task_runtime_service.store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="completed",
            summary="validated",
            completion=TaskCompletionEvaluation(
                status="completed",
                safe_to_report_success=True,
                expected_outcomes=["validation_result"],
                fulfilled_outcomes=["validation_result"],
            ),
        ),
    )

    polled = service.poll_continuous_session(session.session_id)

    assert polled is not None
    assert polled.retry_strategy == "Completed"
    assert polled.completion_checks["external_ready"] is True
    assert polled.completion_checks["aipinho_validation"] is True
    assert polled.completion_checks["speaker_truth"] is True


def test_external_auditor_blocks_rewrite_style_output(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)
    run = _stored_run(task_runtime_service)
    session = service.start_continuous_session(
        ContinuousCollaborationStartRequest(provider="external_model", task_run_id=run.run_id)
    )

    payload = service.adapt_and_receive_success_evaluation(
        "gemini",
        session.session_id,
        ExternalAdapterEvaluationRequest(
            provider_output="Em resumo, segue uma versao melhorada da resposta final da AIpinho.",
            confidence=0.9,
        ),
    )

    audit = payload["adapter_output"]["machine_output"]["metadata"]["speaker_truth_audit"]
    assert payload["external_may_execute"] is False
    assert audit["status"] == "review_loop_required"
    assert "external_rewrite_or_summary_forbidden" in audit["violations"]
    assert payload["evaluation_result"]["retry_strategy"] == "Retry"


def test_ccr_core_has_no_provider_branching():
    files = [
        Path(r"C:\Dev\AIpinho\src\aipinho\services\external_collaboration_service.py"),
        Path(r"C:\Dev\AIpinho\src\aipinho\api\routers\external_collaboration_router.py"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)

    assert "if provider ==" not in text
    assert "switch(provider" not in text
    assert "gemini_mode" not in text
    assert "/gemini" not in text
