from __future__ import annotations
from uuid import uuid4
from aipinho.schemas.ux.ux_copy_payload import UXCopyPayload
from aipinho.services.events.event_core import contains_secret, redact_payload
class UXCopyService:
    def copy(self,text:str,allow_secret_redaction:bool=True)->UXCopyPayload:
        if contains_secret(text) and not allow_secret_redaction: return UXCopyPayload(copy_id=f"copy_{uuid4().hex}",allowed=False,blocked_reasons=["secret_detected"])
        return UXCopyPayload(copy_id=f"copy_{uuid4().hex}",allowed=True,text=str(redact_payload(text)))
