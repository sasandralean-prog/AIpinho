from aipinho.schemas.context.contracts import ContextBundle, ContextScope
from aipinho.schemas.skills.contracts import SkillDryRunRequest
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.skills.skill_dry_run_service import SkillDryRunService

def test_dry_run_simulates_without_execution():
    bundle=ContextBundle(request_id='r',purpose='skill_execution_future',scope=ContextScope()); ContextBundleRepository().save(bundle); result=SkillDryRunService().dry_run(SkillDryRunRequest(skill_id='aipinho.context_explainer',context_bundle_id=bundle.bundle_id)); assert result.status=='completed'; assert result.side_effects_performed is False
