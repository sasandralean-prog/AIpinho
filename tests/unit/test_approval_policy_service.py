from aipinho.services.policy_kernel.approval_policy_service import ApprovalPolicyService


def test_write_files_requires_approval():
    assert ApprovalPolicyService().load().requires_approval("write_files") is True


def test_apply_patch_never_auto_executes():
    service = ApprovalPolicyService().load()

    assert service.requires_approval("apply_patch") is True
    assert service.never_auto_execute("apply_patch") is True


def test_patch_preview_can_preview_without_approval():
    service = ApprovalPolicyService().load()

    assert service.can_preview_without_approval("patch_preview") is True
    assert service.requires_approval("patch_preview") is False


def test_unknown_action_requires_approval_or_deny():
    service = ApprovalPolicyService().load()

    assert service.requires_approval("teleport_files") is True
    assert service.never_auto_execute("teleport_files") is True