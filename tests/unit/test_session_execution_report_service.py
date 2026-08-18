from __future__ import annotations

from types import SimpleNamespace

from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.session_execution_report_service import SessionExecutionReportService


class FakeMessages:
    def list(self, session_id: str | None = None, limit: int = 200):
        return [
            SimpleNamespace(
                metadata={
                    "preview_id": "patch_plan_report",
                    "approval_id": "approval_report",
                }
            )
        ]


class FakeFileResult:
    def model_dump(self):
        return {"file_path": "src/main/App.kt", "changed": True}


class FakePatchApply:
    def list_runs(self, **filters):
        return [SimpleNamespace(apply_run_id="patch_apply_run_report", status="completed")]

    def get_result(self, apply_run_id: str):
        return SimpleNamespace(
            status="completed",
            safe_to_report_success=True,
            files=[FakeFileResult()],
            post_apply_validation=SimpleNamespace(passed=True, blocking_reasons=[]),
        )


class FakePlanStore:
    def get_plan(self, plan_id: str):
        return SimpleNamespace(
            status="needs_review",
            workspace="C:\\target",
            source_id="task_run_readonly",
            quality_gate={"status": "passed"},
            blocked_reasons=[],
        )


def test_session_execution_report_uses_session_records_without_execution() -> None:
    decision = ChatOperationDecision(
        operation_id="chatop_report",
        operation_type="session_execution_report",
        message_type="assistant_final_answer",
        confidence=0.9,
    )
    response = SessionExecutionReportService(
        message_service=FakeMessages(),
        patch_apply_service=FakePatchApply(),
        plan_store=FakePlanStore(),
    ).report("chat_report", decision)

    assert response.status == "ok"
    assert response.operation_type == "session_execution_report"
    assert response.is_final_answer is True
    assert response.policy["executes_tools"] is False
    assert "patch_apply_run_report" in {item["ref_id"] for item in response.evidence_refs}
    assert "src/main/App.kt" in response.message
