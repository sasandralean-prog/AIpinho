from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from aipinho.schemas.chat.session_state import SessionState
from aipinho.services.session.session_state_reconciliation_service import SessionStateReconciliationService


class FakeDrafts:
    def __init__(self, draft):
        self.draft = draft

    def get(self, _draft_id):
        return self.draft


class FakeRuns:
    def __init__(self, runs):
        self.runs = runs

    def list_runs(self, **_filters):
        return self.runs


def _state(*, expires_at=None, draft_id="draft_test"):
    now = datetime.now(timezone.utc).isoformat()
    return SessionState(
        session_id="session_test",
        created_at=now,
        updated_at=now,
        expires_at=expires_at,
        active_task_draft_id=draft_id,
    )


def test_expired_session_clears_active_task_draft():
    service = SessionStateReconciliationService(
        drafts=FakeDrafts(None),
        runs=FakeRuns([]),
    )

    state, reasons = service.reconcile(
        _state(expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
    )

    assert state.status == "expired"
    assert state.active_task_draft_id is None
    assert reasons == ["session_expired"]


def test_terminal_task_run_clears_active_draft_reference():
    draft = SimpleNamespace(status="preview_ready", expires_at=None)
    service = SessionStateReconciliationService(
        drafts=FakeDrafts(draft),
        runs=FakeRuns([SimpleNamespace(status="completed")]),
    )

    state, reasons = service.reconcile(_state())

    assert state.active_task_draft_id is None
    assert reasons == ["active_task_runs_terminal"]


def test_nonterminal_task_run_keeps_active_draft_reference():
    draft = SimpleNamespace(status="preview_ready", expires_at=None)
    service = SessionStateReconciliationService(
        drafts=FakeDrafts(draft),
        runs=FakeRuns([SimpleNamespace(status="running")]),
    )

    state, reasons = service.reconcile(_state())

    assert state.active_task_draft_id == "draft_test"
    assert reasons == []
