from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.services.patching.patch_source_resolver import PatchSourceResolver


def test_patch_source_resolver_sources():
    evidence, warnings, blocked = PatchSourceResolver().resolve(PatchPlanRequest(workspace="w", source_type="project_report", source_id="r", affected_files=["a.py"]))
    assert evidence
    assert warnings
    assert not blocked
    _, _, blocked = PatchSourceResolver().resolve(PatchPlanRequest(workspace="w", source_type="unknown"))
    assert "source_type_not_allowed" in blocked
