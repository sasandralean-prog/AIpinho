from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.schemas.tasks.task_draft_event import TaskDraftEvent
from aipinho.services.orchestration.task_contract_builder import TaskContractBuilder
from aipinho.services.orchestration.task_draft_policy_service import TaskDraftPolicyService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.services.session.session_store import utc_now


class TaskContractDraftService:
    def __init__(
        self,
        store: TaskDraftStore | None = None,
        policy: TaskDraftPolicyService | None = None,
        builder: TaskContractBuilder | None = None,
        prompt_intelligence: PromptIntelligenceService | None = None,
        policy_decisions: EffectivePolicyDecisionService | None = None,
    ) -> None:
        self.store = store or TaskDraftStore()
        self.policy = policy or TaskDraftPolicyService().load()
        self.builder = builder or TaskContractBuilder(policy=self.policy)
        self.prompt_intelligence = prompt_intelligence or PromptIntelligenceService()
        self.policy_decisions = policy_decisions or EffectivePolicyDecisionService()

    def create_from_analysis(self, intent_map, policy_decision, session_state=None):
        draft = self.builder.build_draft(intent_map, policy_decision, session_state=session_state)
        if draft is None:
            return None
        self.store.save(draft)
        self.append_event(draft.draft_id, "draft_created", f"Draft criado com status {draft.status}.")
        return draft

    def create_from_prompt(self, prompt: str, session_state=None):
        analysis = self.prompt_intelligence.analyze(PromptAnalysisRequest(prompt=prompt))
        policy_request = self.prompt_intelligence.to_policy_request(analysis.intent_map)
        decision, _canonical = self.policy_decisions.resolve_policy_request(policy_request)
        return self.create_from_analysis(analysis.intent_map, decision, session_state=session_state)

    def get_draft(self, draft_id: str):
        return self.store.get(draft_id)

    def delete_draft(self, draft_id: str) -> bool:
        if self.get_draft(draft_id) is not None:
            self.append_event(draft_id, "draft_deleted", "Draft removido.")
        return self.store.delete(draft_id)

    def list_events(self, draft_id: str) -> list[TaskDraftEvent]:
        return self.store.list_events(draft_id)

    def append_event(self, draft_id: str, event_type, summary: str, data: dict | None = None) -> TaskDraftEvent:
        event = TaskDraftEvent(
            event_id=f"draft_event_{uuid4().hex}",
            draft_id=draft_id,
            event_type=event_type,
            created_at=utc_now(),
            summary=summary,
            data=data or {},
        )
        self.store.append_event(event)
        return event

    def refresh_policy(self, draft_id: str):
        draft = self.get_draft(draft_id)
        if draft is None:
            return None
        self.append_event(draft_id, "policy_refreshed", "Policy refresh solicitado; draft permanece non-executing.")
        return draft

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        store_status = self.store.status()
        overall = "ok" if policy_status.get("status") == store_status.get("status") == "ok" else "degraded"
        return {"status": overall, "service": "task_contract_draft", "policy": policy_status, "store": store_status, "execution_enabled": False}
