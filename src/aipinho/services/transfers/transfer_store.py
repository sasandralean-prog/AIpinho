from __future__ import annotations
import json
from aipinho.core.paths import PATHS
class TransferStore:
    def __init__(self,folder:str): self.root=PATHS.project_root/"data"/"runtime"/"transfers"/folder
    def save(self,job_id:str,payload:dict[str,object])->dict[str,object]:
        self.root.mkdir(parents=True,exist_ok=True); (self.root/f"{job_id}.json").write_text(json.dumps(payload,indent=2,ensure_ascii=True),encoding="utf-8"); return payload
    def get(self,job_id:str)->dict[str,object]|None:
        path=self.root/f"{job_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
