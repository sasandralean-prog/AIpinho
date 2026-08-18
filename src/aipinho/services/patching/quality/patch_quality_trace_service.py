from __future__ import annotations

from aipinho.schemas.patching.quality.patch_quality_trace import PatchQualityTrace


class PatchQualityTraceService:
    def create(self, quality_id: str) -> PatchQualityTrace:
        return PatchQualityTrace(quality_id=quality_id, events=["patch_quality_gate_started"])

    def add(self, trace: PatchQualityTrace, event: str) -> PatchQualityTrace:
        trace.events.append(event)
        return trace

    def finish(self, trace: PatchQualityTrace, status: str) -> PatchQualityTrace:
        trace.events.append(f"patch_quality_gate_finished:{status}")
        return trace

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_quality_trace", "execution_enabled": False}
