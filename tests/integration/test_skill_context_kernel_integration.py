from aipinho.schemas.context.contracts import ContextBundle,ContextScope
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.skills.skill_context_requirement_service import SkillContextRequirementService
from aipinho.services.skills.skill_registry_service import SkillRegistryService

def test_context_kernel_bundle_is_required_and_owned():
    skill=SkillRegistryService().get('aipinho.context_explainer'); assert SkillContextRequirementService().validate(skill,None)['status']=='blocked'; b=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(b); result=SkillContextRequirementService().validate(skill,b.bundle_id); assert result['status']=='allowed'; assert result['context_owner']=='context_kernel'
