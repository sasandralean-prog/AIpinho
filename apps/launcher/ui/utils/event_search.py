from __future__ import annotations
def search_events(events:list[dict[str,object]],query:str)->list[dict[str,object]]:
    q=query.lower().strip()
    if not q: return events
    return [e for e in events if q in " ".join(str(e.get(k,"")) for k in ("event_type","source_service","human_summary","severity","status")).lower()]
