from aipinho.schemas.skills.contracts import SkillRouteRequest
from aipinho.services.skills.skill_router_service import SkillRouterService

def test_routes_context_explainer_without_execution():
    result=SkillRouterService().route(SkillRouteRequest(category='context', purpose='explain admitted context')); assert result.candidates[0].skill_id=='aipinho.context_explainer'; assert result.execution_started is False
