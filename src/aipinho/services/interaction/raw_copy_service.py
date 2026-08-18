from __future__ import annotations
from aipinho.schemas.interaction.raw_copy_result import RawCopyResult
from aipinho.services.events.event_core import contains_secret
from aipinho.services.interaction.raw_viewer_service import RawViewerService
class RawCopyService:
    def copy(self,raw_ref_id:str,max_chars:int=50000)->RawCopyResult:
        text=RawViewerService().viewer(raw_ref_id,max_chars=max_chars).sanitized_text
        if contains_secret(text): return RawCopyResult(raw_ref_id=raw_ref_id,allowed=False,blocked_reasons=["secret_detected_after_redaction"])
        return RawCopyResult(raw_ref_id=raw_ref_id,allowed=True,text=text)
