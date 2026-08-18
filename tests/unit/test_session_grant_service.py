from __future__ import annotations

from datetime import timedelta

from aipinho.services.chat.session_grant_service import SessionGrantService, _utc_now


def test_session_grant_approve_and_scope(tmp_path):
    service = SessionGrantService(store_dir=tmp_path)
    grant = service.create_pending(
        session_id="chat_test",
        workspace_id="workspace_a",
        workspace_path=str(tmp_path),
        actions=["create_file"],
        paths_scope=[str(tmp_path)],
    )

    decision = service.approve(grant.grant_id, actor="test")

    assert decision.status == "approved"
    assert service.is_effective(grant.grant_id, action="create_file", path=str(tmp_path / "ok.txt")).reason_code == "grant_effective"
    assert service.is_effective(grant.grant_id, action="delete_file", path=str(tmp_path / "ok.txt")).reason_code == "grant_action_out_of_scope"


def test_session_grant_expires(tmp_path):
    service = SessionGrantService(store_dir=tmp_path)
    grant = service.create_pending(
        session_id="chat_test",
        workspace_id="workspace_a",
        workspace_path=str(tmp_path),
        actions=["read_file"],
        paths_scope=[str(tmp_path)],
    )
    grant.expires_at = _utc_now() - timedelta(seconds=1)
    service.save(grant)

    decision = service.approve(grant.grant_id, actor="test")

    assert decision.status == "expired"
    assert decision.reason_code == "grant_not_pending:expired"
