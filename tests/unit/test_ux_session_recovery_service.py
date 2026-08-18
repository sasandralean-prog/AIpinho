from aipinho.services.ux.ux_session_recovery_service import UXSessionRecoveryService
def test_session_recovery_preserves_draft(tmp_path):
    svc=UXSessionRecoveryService(tmp_path/"state.json"); state=svc.restore({"session_id":"s","cursor":"9","draft":"ola"}); assert state.draft=="ola" and svc.get().cursor=="9"
