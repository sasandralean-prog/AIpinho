from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.schemas.web_search import WebSearchResult, WebSearchSource
from aipinho.services.sandbox_file_writer_service import SandboxFileWriterService


def _client() -> TestClient:
    return TestClient(create_app())


def _session(client: TestClient) -> str:
    response = client.post("/api/v1/chat/sessions", json={"title": "runtime parity regression"})
    assert response.status_code == 200
    return response.json()["session"]["session_id"]


def _send(client: TestClient, session_id: str, prompt: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"role": "user", "content": prompt, "metadata": {}},
    )
    assert response.status_code == 200
    return response.json()["chat_response"]


def test_persistent_chat_public_fact_uses_web_sources(monkeypatch) -> None:
    def fake_search(self, query: str, max_results: int | None = None, freshness: str | None = None) -> WebSearchResult:
        return WebSearchResult(
            status="ready",
            query=query,
            provider_id="test_web_provider",
            source_count=1,
            searched_at="2026-06-18T00:00:00+00:00",
            results=[
                WebSearchSource(
                    title="Fonte publica testavel",
                    url="https://example.com/public-source",
                    snippet="Fonte publica usada no fluxo real do chat persistente.",
                    source_name="test_web_provider",
                    retrieved_at="2026-06-18T00:00:00+00:00",
                    reliability_hint="test_provider",
                )
            ],
            warnings=["test_web_provider"],
        )

    monkeypatch.setattr("aipinho.services.web_search_provider_service.WebSearchProviderService.search", fake_search)

    client = _client()
    chat_response = _send(
        client,
        _session(client),
        "Nome dos 10 ?ltimos governadores do Rio de Janeiro. Use fontes.",
    )

    assert chat_response["status"] in {"ok", "ready"}
    assert chat_response["operation_type"] == "web_search_required"
    assert chat_response["message_type"] == "assistant_final_answer"
    assert chat_response["intent"]["requires_web_search"] is True
    assert chat_response["intent"]["private_rag_required"] is False
    assert "Resumo:" in chat_response["message"]
    assert "Fonte publica usada no fluxo real do chat persistente" in chat_response["message"]
    assert chat_response["citation_map"]["sources"][0]["url"] == "https://example.com/public-source"


def test_persistent_chat_sandbox_batch_without_executable_plan_returns_preview() -> None:
    sandbox_root = SandboxFileWriterService().root
    target = (sandbox_root / "runtime_parity_test").resolve(strict=False)
    if str(target).startswith(str(sandbox_root)) and target.exists():
        shutil.rmtree(target)
    try:
        client = _client()
        chat_response = _send(
            client,
            _session(client),
            (
                f"Crie a pasta {target}, gere tres arquivos txt dentro dela, "
                "depois gere um zip chamado runtime_parity_test.zip contendo esses tres arquivos. "
                "Ao final valide que o zip existe e tem tamanho maior que zero."
            ),
        )

        archive_path = target / "runtime_parity_test.zip"
        assert chat_response["status"] == "preview"
        assert chat_response["operation_type"] == "artifact_zip_generate"
        assert chat_response["task_id"] is None
        assert chat_response["approval_id"] is None
        assert not archive_path.exists()
        assert "canonical_lifecycle:APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN" in chat_response["warnings"]
        assert chat_response["policy"]["canonical_lifecycle"]["safe_to_report_success"] is False
    finally:
        if str(target).startswith(str(sandbox_root)) and target.exists():
            shutil.rmtree(target)


def test_persistent_chat_forbidden_root_blocks_write() -> None:
    client = _client()
    chat_response = _send(
        client,
        _session(client),
        r"Crie um arquivo em C:\Windows\System32\aipinho_teste.txt com o texto teste.",
    )

    assert chat_response["status"] == "blocked"
    assert chat_response["operation_type"] == "filesystem_write_file"
    assert "forbidden_root" in chat_response["warnings"]


def test_persistent_chat_apk_request_is_preview_not_fake_success() -> None:
    client = _client()
    chat_response = _send(
        client,
        _session(client),
        r"Crie um projeto Android Kotlin simples em C:\Dev\AIpinho\sandboxes\AppTeste e gere um APK.",
    )

    assert chat_response["status"] == "preview"
    assert chat_response["operation_type"] == "android_apk_build"
    assert chat_response["message_type"] == "task_preview"
    assert chat_response["is_final_answer"] is False
    assert chat_response["grounding_missing_reason"] == "task_preview_not_execution_result"



def test_active_run_limit_saturation_returns_visible_status(monkeypatch) -> None:
    def fake_queue_health(self, max_age_hours: int = 1, worker_pool_capacity: int = 8) -> dict[str, object]:
        return {
            "status": "ok",
            "active_runs": worker_pool_capacity,
            "queued_runs": 0,
            "stale_runs": 0,
            "pending_approvals": 0,
            "active_sessions": 1,
            "dispatcher_status": "saturated",
            "worker_pool_capacity": worker_pool_capacity,
            "worker_pool_available_slots": 0,
            "reason_code": "active_run_limit_reached",
            "backpressure_required": True,
        }

    monkeypatch.setattr("aipinho.services.runtime.runtime_state_hygiene_service.RuntimeStateHygieneService.queue_health", fake_queue_health)
    client = _client()
    session_id = _session(client)

    response = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"role": "user", "content": "Ola", "metadata": {}})
    payload = response.json()

    assert response.status_code == 200
    assert payload["chat_response"]["status"] == "degraded"
    assert "active_run_limit_reached" in payload["chat_response"]["warnings"]
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["content"]


def test_no_silent_message_after_persistent_chat_send() -> None:
    client = _client()
    session_id = _session(client)

    payload = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"role": "user", "content": "oi", "metadata": {}}).json()

    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["content"].strip()
