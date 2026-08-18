from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.patch_plan import PatchPlan


class PatchPlanResult(AIpinhoModel):
    status: str
    plan: PatchPlan
    apply_enabled: bool = False
    write_enabled: bool = False
