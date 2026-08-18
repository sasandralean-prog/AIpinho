from __future__ import annotations
def filter_events(events:list[dict[str,object]],severity:str|None=None,status:str|None=None)->list[dict[str,object]]:
    return [e for e in events if (severity is None or e.get("severity")==severity) and (status is None or e.get("status")==status) and e.get("visibility") not in {"hidden","internal"}]
