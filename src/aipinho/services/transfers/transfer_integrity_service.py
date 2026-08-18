from __future__ import annotations
import hashlib
from aipinho.schemas.transfers.transfer_integrity_result import TransferIntegrityResult
class TransferIntegrityService:
    def verify(self,job_id:str,content:bytes=b"",expected_sha256:str|None=None,actual_sha256:str|None=None)->TransferIntegrityResult:
        actual=actual_sha256 or hashlib.sha256(content).hexdigest()
        if not expected_sha256: return TransferIntegrityResult(job_id=job_id,status="degraded",actual_sha256=actual,verified=False,human_message="Hash esperado ausente.")
        ok=actual.lower()==expected_sha256.lower()
        return TransferIntegrityResult(job_id=job_id,status="ok" if ok else "mismatch",expected_sha256=expected_sha256,actual_sha256=actual,verified=ok,human_message="Integridade verificada." if ok else "Hash do download nao confere.")
