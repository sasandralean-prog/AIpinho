from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService


def _draft(prompt: str, tmp_path):
    pi = PromptIntelligenceService()
    analysis = pi.analyze(PromptAnalysisRequest(prompt=prompt))
    decision = PolicyKernelService().resolve(pi.to_policy_request(analysis.intent_map))
    service = TaskContractDraftService(store=TaskDraftStore(tmp_path))
    return service.create_from_analysis(analysis.intent_map, decision)


def test_conversation_does_not_create_draft(tmp_path):
    assert _draft("Bom dia, tudo certo?", tmp_path) is None


def test_readonly_creates_non_executing_draft(tmp_path):
    draft = _draft(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada", tmp_path)
    assert draft is not None
    assert draft.contract_type == "readonly_analysis"
    assert draft.workspace.status == "confirmed"
    assert draft.safe_to_execute is False


def test_artifact_creates_approval_or_clarification_draft(tmp_path):
    draft = _draft("Salve um relatorio em reports/final.md", tmp_path)
    assert draft is not None
    assert draft.contract_type == "artifact_generation"
    assert "write_files" in draft.requested_actions
    assert draft.safe_to_execute is False


def test_patch_creates_draft_without_execution(tmp_path):
    draft = _draft(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    assert draft is not None
    assert draft.contract_type == "patch_request"
    assert "apply_patch" in draft.requested_actions
    assert draft.safe_to_execute is False


def test_forbidden_root_draft_blocked(tmp_path):
    draft = _draft(r"Corrija C:\PinhoabacaxiAI", tmp_path)
    assert draft is not None
    assert draft.status == "blocked"
    assert draft.workspace.status == "protected"


def test_ambiguity_draft_needs_clarification(tmp_path):
    draft = _draft("Arrume tudo", tmp_path)
    assert draft is not None
    assert draft.status == "needs_clarification"
    assert draft.clarifying_questions