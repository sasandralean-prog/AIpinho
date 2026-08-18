from __future__ import annotations

from pathlib import Path

from aipinho.app_factory import create_app
from aipinho.schemas.external_collaboration import (
    ExternalAdapterReviewRequest,
    ExternalReviewCreateRequest,
    ExternalTaskCreateRequest,
    SuccessContractCreateRequest,
)
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


def test_success_contract_is_created_with_aipinho_ownership(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)

    contract = service.create_success_contract(
        SuccessContractCreateRequest(
            objective="Gerar APK validado.",
            acceptance_criteria=["APK existe", "validacao passou"],
            forbidden=["nao fingir sucesso"],
            required_evidence=["artifact_id"],
            completion_definition="APK baixavel e validado.",
        )
    )

    assert contract.success_contract_id.startswith("success_contract_")
    assert contract.owner == "aipinho"
    assert contract.acceptance_criteria == ["APK existe", "validacao passou"]


def test_external_task_creates_task_run_and_uses_universal_session(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)

    payload = service.submit_task(
        ExternalTaskCreateRequest(
            provider="external_model",
            objective="Acompanhar task publica.",
            expected_output="Resumo governado.",
        )
    )

    task_run_id = payload["task_run_id"]
    assert task_run_id
    assert payload["external_may_execute"] is False
    assert payload["universal_task_session"]["task_run_id"] == task_run_id
    assert payload["universal_task_session"]["metadata"]["canonical_source"] == "task_run_store"

    progress = service.task_progress(payload["external_task"]["external_task_id"])
    assert progress["source"] == "universal_task_session"
    assert progress["task_run_id"] == task_run_id


def test_external_review_is_registered_without_execution_authority(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)

    review = service.receive_review(
        ExternalReviewCreateRequest(
            provider="external_model",
            status="completed",
            confidence=0.8,
            raw_summary="Build parece OK, mas precisa evidencia.",
            recommendations=["Conferir artifacts pela AIpinho."],
        )
    )

    assert review.review_id.startswith("external_review_")
    assert review.may_execute is False
    assert review.replaces_internal_reviewer is False
    assert review.authority_decision == "received_for_internal_interpretation"


def test_gemini_adapter_generates_human_and_machine_outputs_without_privilege(tmp_path, task_runtime_service):
    service = _service(tmp_path, task_runtime_service)

    payload = service.adapt_and_receive_review(
        "gemini",
        ExternalAdapterReviewRequest(
            provider_output="O build terminou. APK criado. Resta revisar assets.",
            confidence=0.9,
        ),
    )

    assert payload["status"] == "ok"
    assert payload["external_may_execute"] is False
    assert payload["adapter_output"]["human_output"]
    assert payload["adapter_output"]["machine_output"]["provider"] == "gemini"
    assert payload["review"]["may_execute"] is False
    assert "Revisar evidencias de build" in payload["adapter_output"]["machine_output"]["recommendations"][0]
    assert payload["adapter_output"]["machine_output"]["metadata"]["speaker_truth_mode"] == "auditor"


def test_external_routes_do_not_create_model_specific_paths():
    app = create_app()
    external_paths = sorted(route.path for route in app.routes if route.path.startswith("/api/v1/external"))

    assert "/api/v1/external/adapters/{adapter_id}/review" in external_paths
    assert "/api/v1/external/delegations" in external_paths
    assert "/api/v1/external/delegations/{delegation_id}/poll" in external_paths
    assert all("gemini" not in path.lower() for path in external_paths)
    assert any(path == "/api/v1/external/tasks/{external_task_id}/progress" for path in external_paths)


def test_new_external_services_do_not_branch_on_specific_provider_names():
    files = [
        Path(r"C:\Dev\AIpinho\src\aipinho\services\external_collaboration_service.py"),
        Path(r"C:\Dev\AIpinho\src\aipinho\api\routers\external_collaboration_router.py"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()

    assert "if provider == " not in text
    assert "if adapter_id == " not in text
