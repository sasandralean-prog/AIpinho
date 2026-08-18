from aipinho.schemas.context.contracts import ContextBundle,ContextScope
from aipinho.schemas.skills.contracts import SkillPreviewRequest
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.skills.skill_preview_service import SkillPreviewService

def test_authority_and_contract_expansion_blocked():
    b=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(b); result=SkillPreviewService().preview(SkillPreviewRequest(skill_id='aipinho.patch_planner',context_bundle_id=b.bundle_id,granted_capabilities=['patch_preview'],task_contract={'allowed_capabilities':[],'selected_model':'x'})); assert result.status=='blocked'; assert any('contract_expansion_blocked' in x for x in result.blocked_reasons); assert any('selected_model' in x for x in result.blocked_reasons)
