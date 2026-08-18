from __future__ import annotations
from aipinho.schemas.ux.ux_latency_indicator import UXLatencyIndicator
class UXLatencyService:
    def indicator(self,target:str,latency_ms:int|None)->UXLatencyIndicator:
        if latency_ms is None: return UXLatencyIndicator(target=target,state="unknown",human_message="Latencia desconhecida.")
        state="healthy" if latency_ms<1000 else ("degraded" if latency_ms<5000 else "down")
        return UXLatencyIndicator(target=target,latency_ms=latency_ms,state=state,human_message=f"{latency_ms} ms")
