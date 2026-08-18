from __future__ import annotations
import json
from aipinho.schemas.interaction.raw_viewer_result import RawViewerResult
from aipinho.services.events.event_core import EventRawPayloadStore, redact_payload
class RawViewerService:
    def viewer(self,raw_ref_id:str,max_chars:int=50000)->RawViewerResult:
        raw=EventRawPayloadStore().read(raw_ref_id); sanitized=json.dumps(redact_payload(raw),indent=2,ensure_ascii=True); truncated=len(sanitized)>max_chars; text=sanitized[:max_chars]
        return RawViewerResult(raw_ref_id=raw_ref_id,status="ok",sanitized_text=text,hidden_by_default=True,line_count=text.count("\n")+1 if text else 0,truncated=truncated,warnings=["truncated"] if truncated else [])
