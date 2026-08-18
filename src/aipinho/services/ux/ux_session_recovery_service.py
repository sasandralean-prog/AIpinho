from __future__ import annotations
import json
from pathlib import Path
from aipinho.core.paths import PATHS
from aipinho.schemas.ux.ux_session_recovery import UXSessionRecovery
class UXSessionRecoveryService:
    def __init__(self,path:Path|None=None): self.path=path or PATHS.project_root/"data"/"runtime"/"ux"/"session_recovery"/"state.json"
    def get(self):
        if not self.path.exists(): return UXSessionRecovery(stale=True)
        return UXSessionRecovery(**json.loads(self.path.read_text(encoding="utf-8")))
    def save(self,state:UXSessionRecovery):
        self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps(state.model_dump(),indent=2,ensure_ascii=True),encoding="utf-8"); return state
    def restore(self,payload:dict[str,object]):
        merged=self.get().model_dump()
        for key in {"session_id","cursor","draft","last_snapshot","stale"}:
            if key in payload: merged[key]=payload[key]
        return self.save(UXSessionRecovery(**merged))
