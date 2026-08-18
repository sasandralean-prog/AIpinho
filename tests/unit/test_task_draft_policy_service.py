from aipinho.services.orchestration.task_draft_policy_service import TaskDraftPolicyService


def test_task_draft_policy_intent_sets_and_safe_default():
    policy = TaskDraftPolicyService().load()
    assert policy.should_create_for_intent("readonly_analysis") is True
    assert policy.should_create_for_intent("patch_request") is True
    assert policy.should_create_for_intent("conversation") is False
    assert policy.safe_to_execute_default() is False
    assert policy.require_workspace_confirmation() is True