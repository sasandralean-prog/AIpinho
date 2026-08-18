from aipinho.services.supervisor.mobile_pairing_service import MobilePairingService
from aipinho.services.security.local_token_service import LocalTokenService


def test_mobile_pairing_token_once_rotate_and_status_hides_plaintext(tmp_path):
    svc = MobilePairingService(LocalTokenService(tmp_path / "token.json"))
    created = svc.create_token()
    assert created.token
    assert svc.status()["plaintext_available"] is False
    assert svc.status()["token_configured"] is True
    assert svc.verify(created.token)["status"] == "verified"
    rotated = svc.rotate_token()
    assert svc.verify(created.token)["status"] == "invalid"
    assert svc.verify(rotated.token)["status"] == "verified"
