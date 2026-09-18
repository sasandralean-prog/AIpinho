from types import SimpleNamespace

from aipinho.schemas.runtime.runtime_truth import RuntimeTruth
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.task_run_chat_result_publisher_service import (
    TaskRunChatResultPublisherService,
)
from tests.support.runtime_fixtures import runtime_run


class FakeSessionService:
    def get(self, session_id):
        return {"session_id": session_id} if session_id == "chat_test" else None


class FakeMessageService:
    def __init__(self):
        self.messages = []

    def list(self, session_id=None, limit=500):
        return [
            message
            for message in self.messages
            if session_id is None or message.session_id == session_id
        ][-limit:]

    def create(self, session_id, request):
        message = SimpleNamespace(
            message_id=f"msg_{len(self.messages) + 1}",
            session_id=session_id,
            role=request.role,
            content=request.content,
            task_id=request.task_id,
            metadata=request.metadata,
        )
        self.messages.append(message)
        return message


class FakeResultIndex:
    def __init__(self):
        self.calls = []

    def add_final_answer(self, session_id, response, message_id):
        self.calls.append((session_id, response, message_id))
        return "result_test"


class FakeEventPublisher:
    def __init__(self):
        self.requests = []

    def publish(self, request):
        self.requests.append(request)
        return SimpleNamespace(event_id="event_test")


def _publisher():
    messages = FakeMessageService()
    index = FakeResultIndex()
    events = FakeEventPublisher()
    service = TaskRunChatResultPublisherService(
        session_service=FakeSessionService(),
        message_service=messages,
        result_index=index,
        event_publisher=events,
    )
    return service, messages, index, events


def test_completed_task_result_is_published_to_origin_chat_once():
    service, messages, index, events = _publisher()
    run = runtime_run(status="completed")
    run.session_id = "chat_test"
    run.intent_map = {"intent_type": "readonly_project_analysis"}
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="Análise concluída.",
        outputs={
            "project_report": {
                "report_id": "report_test",
                "rendered_markdown": "# Relatório\n\nResultado fundamentado.",
            }
        },
        validation={"validation_id": "validation_test", "status": "passed"},
    )

    first = service.publish(run, result)
    second = service.publish(run, result)

    assert first["status"] == "published"
    assert second["status"] == "already_published"
    assert len(messages.messages) == 1
    assert messages.messages[0].task_id == run.task_id
    assert messages.messages[0].metadata["task_run_id"] == run.run_id
    assert messages.messages[0].metadata["approval_required"] == "False"
    assert messages.messages[0].metadata["message_type"] == "assistant_final_answer"
    assert "Resultado fundamentado" in messages.messages[0].content
    assert len(index.calls) == 1
    assert events.requests[0].payload["task_id"] == run.task_id
    assert events.requests[0].payload["task_run_id"] == run.run_id


def test_task_result_without_persistent_chat_is_not_published():
    service, messages, index, _events = _publisher()
    run = runtime_run(status="completed")
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="Análise concluída.",
    )

    published = service.publish(run, result)

    assert published == {
        "status": "skipped",
        "reason": "persistent_chat_session_not_found",
    }
    assert messages.messages == []
    assert index.calls == []


def test_completed_phase_with_unsafe_mission_truth_is_published_as_degraded():
    service, messages, index, _events = _publisher()
    run = runtime_run(status="completed")
    run.session_id = "chat_test"
    run.intent_map = {"intent_type": "workspace_fix_request"}
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="Missão concluída com sucesso.",
        validation={"validation_id": "validation_test", "status": "passed"},
    )
    truth = RuntimeTruth(
        truth_id=f"runtime_truth_{run.run_id}",
        task_run_id=run.run_id,
        status="partial",
        reason_code="mission_completion_insufficient_evidence",
        safe_to_report_success=False,
        mission_id="mission_test",
        mission_completion_status="insufficient_evidence",
        mission_completion_safe_to_report_success=False,
        mission_completion_reason_codes=[
            "MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"
        ],
        mission_completion_authority_sha256="a" * 64,
        missing_evidence=[
            "mission_completion:MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"
        ],
        ui_status="partial",
        speaker_truth_status="evidence_required",
    )

    published = service.publish(
        run,
        result,
        runtime_truth=truth,
    )

    assert published["status"] == "published"
    assert len(messages.messages) == 1
    message = messages.messages[0]
    assert message.metadata["message_type"] == "assistant_degraded_answer"
    assert message.metadata["is_final_answer"] == "False"
    assert message.metadata["runtime_truth_status"] == "partial"
    assert (
        message.metadata["mission_completion_status"]
        == "insufficient_evidence"
    )
    assert "Missão concluída com sucesso." not in message.content
    assert "não permite declarar sucesso completo" in message.content
    assert index.calls == []
