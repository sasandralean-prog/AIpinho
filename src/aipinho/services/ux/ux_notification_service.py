from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from aipinho.core.paths import PATHS
from aipinho.schemas.ux.ux_notification import UXNotification
from aipinho.services.events.event_core import contains_secret, redact_payload
def _now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
class UXNotificationService:
    def __init__(self,path:Path|None=None): self.path=path or PATHS.project_root/"data"/"runtime"/"ux"/"notifications"/"notifications.json"
    def _read(self):
        if not self.path.exists(): return []
        return [UXNotification(**i) for i in json.loads(self.path.read_text(encoding="utf-8"))]
    def _write(self,items):
        self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps([i.model_dump() for i in items],indent=2,ensure_ascii=True),encoding="utf-8")
    def list(self): return self._read()
    def notify(self,event_type:str,human_message:str,severity:str="info",dedupe_key:str|None=None):
        if contains_secret(human_message): human_message=str(redact_payload(human_message))
        items=self._read(); key=dedupe_key or f"{event_type}:{human_message}"
        for item in items:
            if item.dedupe_key==key and not item.acknowledged: return item
        item=UXNotification(notification_id=f"uxn_{uuid4().hex}",event_type=event_type,severity=severity,human_message=human_message,dedupe_key=key,created_at=_now()); items.append(item); self._write(items); return item
    def ack(self,notification_ids:list[str]):
        ids=set(notification_ids); items=[]
        for item in self._read():
            if item.notification_id in ids: item.acknowledged=True
            items.append(item)
        self._write(items); return items
