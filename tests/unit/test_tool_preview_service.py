from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.tools.tool_preview_service import ToolPreviewService


def test_tool_call_to_plan():
    plan = ToolPreviewService().plan_from_calls([ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "."})])
    assert plan.source == "direct"
    assert plan.safe_to_execute is False
    assert plan.tool_calls[0].tool_id == "filesystem.read_file"


def test_requested_actions_to_tool_candidates():
    service = ToolPreviewService()
    mapped = service.router.map_actions(["read_files", "write_files", "apply_patch"])
    assert mapped["read_files"] == ["filesystem.read_file"]
    assert mapped["write_files"] == ["filesystem.write_file"]
    assert mapped["apply_patch"] == ["patch.apply"]


def test_draft_to_dry_run_plan_readonly():
    draft = TaskContractDraftService().create_from_prompt(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada")
    assert draft is not None
    plan = ToolPreviewService().plan_from_draft(draft.draft_id)
    assert plan is not None
    assert plan.tool_calls[0].tool_id == "filesystem.read_file"


def test_preview_to_plan_approval_required():
    draft = TaskContractDraftService().create_from_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho")
    preview = TaskPreviewService().create_preview_from_draft(draft.draft_id)
    plan = ToolPreviewService().plan_from_preview(preview.preview_id)
    assert plan is not None
    assert {call.tool_id for call in plan.tool_calls} >= {"patch.preview", "patch.apply"}


def test_blocked_preview_plan():
    draft = TaskContractDraftService().create_from_prompt(r"Corrija C:\PinhoabacaxiAI")
    preview = TaskPreviewService().create_preview_from_draft(draft.draft_id)
    plan = ToolPreviewService().plan_from_preview(preview.preview_id)
    assert plan is not None
    assert plan.blocked is True
