from aipinho.services.transfers.transfer_integrity_service import TransferIntegrityService
def test_integrity_detects_mismatch():
    r=TransferIntegrityService().verify("j",actual_sha256="a",expected_sha256="b"); assert r.status=="mismatch" and not r.verified
