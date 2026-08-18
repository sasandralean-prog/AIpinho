from __future__ import annotations

from aipinho.schemas.patching.apply.patch_apply_trace import PatchApplyTrace


class PatchApplyTraceService:
    def create(self, apply_run_id: str) -> PatchApplyTrace:
        return PatchApplyTrace(apply_run_id=apply_run_id, events=["patch_apply_run_created"])

    def add(self, trace: PatchApplyTrace, event: str) -> PatchApplyTrace:
        trace.events.append(event)
        return trace

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_trace", "execution_enabled": False}
