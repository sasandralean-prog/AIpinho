from __future__ import annotations
from aipinho.core.paths import PATHS
from aipinho.schemas.ux.ux_degraded_state import UXDegradedState
from aipinho.utils.yaml_loader import load_yaml_file
class UXDegradedStateService:
    def __init__(self): self.path=PATHS.config_root/"ux"/"degraded_state_policy.yaml"
    def policy(self): return load_yaml_file(self.path,root=PATHS.project_root)
    def for_state(self, service_id: str, state: str) -> UXDegradedState|None:
        if state in {"healthy","ok","running"}: return None
        key=f"{service_id}_down"; states=self.policy().get("states",{}); data=states.get(key) if isinstance(states,dict) else None
        if not isinstance(data,dict): data={"severity":"warning","human_message":f"{service_id} esta indisponivel ou degradado.","allowed_actions":["retry"]}
        return UXDegradedState(service_id=service_id,state="offline" if state in {"down","offline"} else "degraded",severity=str(data.get("severity","warning")),human_message=str(data.get("human_message","Servico degradado.")),allowed_actions=list(data.get("allowed_actions",[])))
    def consolidate(self, service_states: dict[str,str]) -> list[UXDegradedState]:
        return [item for sid,state in service_states.items() if (item:=self.for_state(sid,state)) is not None]
