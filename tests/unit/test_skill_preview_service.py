from aipinho.schemas.context.contracts import ContextBundle, ContextScope
from aipinho.schemas.skills.contracts import SkillPreviewRequest
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.skills.skill_preview_service import SkillPreviewService

def test_preview_has_no_side_effects():
    bundle=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(bundle); result=SkillPreviewService().preview(SkillPreviewRequest(skill_id='aipinho.context_explainer',context_bundle_id=bundle.bundle_id)); assert result.status=='preview'; assert result.side_effects_performed is False
