from types import SimpleNamespace

from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.governed_write_chat_service import GovernedWriteChatService
from aipinho.schemas.governed_write import GovernedWriteOutcome


class FakeRuntime:
    def __init__(self, status: str) -> None:
        self.status = status
        self.calls = []

    def create_from_preview(self, preview_id, options):
        self.calls.append((preview_id, options))
        return SimpleNamespace(
            run_id="task_run_test",
            status=self.status,
            approval_id="approval_test" if self.status == "waiting_input" else None,
            auto_run_requested=bool(options["start_immediately"]),
        )


def _chat_with_runtime(runtime):
    service = ChatService.__new__(ChatService)
    service.task_runtime_service = runtime
    service._include_trace = lambda _request: False
    return service


def test_approval_preview_materializes_task_and_real_approval_state():
    runtime = FakeRuntime("waiting_input")
    service = _chat_with_runtime(runtime)

    run, status = service._materialize_task_run(
        SimpleNamespace(preview_id="preview_test", status="approval_required"),
        SimpleNamespace(requires_task=True),
        SimpleNamespace(mode="normal"),
    )

    assert status == "pending_approval"
    assert run.run_id == "task_run_test"
    assert run.approval_id == "approval_test"
    assert runtime.calls == [("preview_test", {"start_immediately": False, "include_trace": False})]


def test_preview_mode_never_materializes_or_executes_task():
    runtime = FakeRuntime("queued")
    service = _chat_with_runtime(runtime)

    run, status = service._materialize_task_run(
        SimpleNamespace(preview_id="preview_test", status="preview_ready"),
        SimpleNamespace(requires_task=True),
        SimpleNamespace(mode="preview"),
    )

    assert run is None
    assert status is None
    assert runtime.calls == []


def test_canonical_filesystem_write_reaches_governed_service(monkeypatch):
    service = GovernedWriteChatService()
    monkeypatch.setattr(
        service,
        "execute",
        lambda _request: GovernedWriteOutcome(status="approval_required", run_id="run_test"),
    )
    decision = ChatOperationDecision(
        operation_id="operation_test",
        operation_type="filesystem_write_file",
        message_type="task_status_update",
        confidence=0.9,
        workspace="X:/workspace",
        metadata={
            "router_operation_type": "governed_file_write",
            "requested_operation": "create_file",
            "workspace_write": True,
        },
    )

    response = service.from_decision(
        session_id="session_test",
        prompt="Crie um arquivo de texto no workspace selecionado.",
        decision=decision,
        workspace_ref="X:/workspace",
    )

    assert response is not None
    assert response.status == "pending_approval"
    assert response.task_id == "run_test"
