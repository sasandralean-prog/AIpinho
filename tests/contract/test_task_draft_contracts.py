import pytest
from pydantic import ValidationError

from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace


def test_task_contract_draft_defaults_safe_to_execute_false():
    draft = TaskContractDraft(draft_id="draft_1", created_at="now", updated_at="now")
    assert draft.safe_to_execute is False
    assert draft.workspace.status == "missing"


def test_task_contract_draft_status_enum():
    with pytest.raises(ValidationError):
        TaskContractDraft(draft_id="draft_1", status="running", created_at="now", updated_at="now")


def test_task_draft_workspace_status_enum():
    with pytest.raises(ValidationError):
        TaskDraftWorkspace(path=None, status="active")