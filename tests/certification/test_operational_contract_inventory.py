from __future__ import annotations

import json
from pathlib import Path

import yaml

from aipinho.services.chat.chat_operation_router_service import ChatOperationRouterService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "docs" / "operations"


def test_operational_inventory_has_required_sections_and_operations():
    payload = json.loads((OPS / "aipinho_operational_contract_inventory.json").read_text(encoding="utf-8"))
    required = {
        "operation_types", "workspace_roles", "capabilities_actions", "policy_decisions",
        "approval_requirements", "patch_lifecycle_states", "shell_categories",
        "validation_gates", "artifact_lifecycle", "event_contracts",
        "mobile_viewmodel_states", "block_reason_codes", "regression_candidate_triggers",
        "golden_path_matrix", "mobile_endpoint_parity_matrix",
    }
    assert required.issubset(payload)
    operations = {item["operation_type"] for item in payload["operation_types"]}
    assert {"simple_chat", "artifact_request", "readonly_analysis_with_artifact_output", "patch_apply", "shell_command"}.issubset(operations)
    readonly_artifact = next(item for item in payload["operation_types"] if item["operation_type"] == "readonly_analysis_with_artifact_output")
    assert readonly_artifact["can_read_workspace"] is True
    assert readonly_artifact["can_write_workspace"] is False
    assert readonly_artifact["can_generate_artifact"] is True
    assert readonly_artifact["requires_validation"] is True


def test_block_reason_catalog_is_structured_and_known_to_inventory():
    catalog = yaml.safe_load((ROOT / "config" / "policies" / "block_reason_codes.yaml").read_text(encoding="utf-8"))
    inventory = json.loads((OPS / "aipinho_operational_contract_inventory.json").read_text(encoding="utf-8"))
    codes = {item["code"] for item in catalog["codes"]}
    assert {"source_readonly_write_denied", "preview_missing", "artifact_missing_id", "validation_failed", "unknown_block_reason"}.issubset(codes)
    assert set(inventory["block_reason_codes"]).issubset(codes)
    for item in catalog["codes"]:
        assert item["human_reason_template"]
        assert item["technical_meaning"]
        assert item["safe_alternatives"]
        assert item["mobile_normal_message"]
        assert item["mobile_details_fields"]


def test_golden_path_matrix_covers_success_and_blocking_flows():
    payload = json.loads((OPS / "golden_path_matrix.json").read_text(encoding="utf-8"))
    paths = {item["id"]: item for item in payload["golden_paths"]}
    required = {
        "simple_chat", "simple_chat_with_artifact", "readonly_analysis_with_artifact_output",
        "target_workspace_patch_apply", "blocked_write_to_readonly", "destructive_shell_blocked",
        "artifact_download", "mobile_endpoint_divergence_detection",
    }
    assert required.issubset(paths)
    assert paths["target_workspace_patch_apply"]["expected_approval"] == "required"
    assert "artifact" in paths["artifact_download"]["expected_workspace_behavior"]


def test_workspace_role_contract_denies_write_to_source_readonly(tmp_path):
    workspace = tmp_path / "source"
    workspace.mkdir()
    policy = tmp_path / "workspace_registry.yaml"
    escaped = str(workspace).replace("\\", "\\\\")
    policy.write_text(
        "schema_version: 1\nworkspaces:\n"
        f"  - workspace_id: source_fixture\n    root_path: \"{escaped}\"\n    role: source_readonly\n",
        encoding="utf-8",
    )
    service = WorkspaceRoleContractService(policy).load()
    decision = service.resolve(str(workspace / "file.txt"))
    assert decision.status == "allowed"
    assert decision.contract is not None
    assert decision.contract.read_allowed is True
    assert decision.contract.write_allowed is False
    allowed, reason = service.operation_allowed(decision.contract, "create_file")
    assert allowed is False
    assert reason in {"operation_forbidden_by_workspace_role", "workspace_role_denies_write"}


def test_chat_operation_classifier_keeps_simple_chat_separate_from_task_and_artifact():
    decision = ChatOperationRouterService().route("Quanto e 2 + 2?")
    assert decision.operation_type == "conversation"
    assert decision.metadata.get("router_operation_type") == "simple_conversation"
    assert decision.message_type == "assistant_final_answer"
    assert decision.workspace is None
    assert decision.metadata.get("requested_output") is None


def test_mobile_parity_blocks_are_not_rendered_as_healthy():
    payload = json.loads((OPS / "aipinho_operational_contract_inventory.json").read_text(encoding="utf-8"))
    states = {item["state"]: item for item in payload["mobile_endpoint_parity_matrix"]}
    blocked = states["blocked"]
    assert "blocked" in blocked["mobile_normal_expected"]
    assert "healthy" not in blocked["mobile_normal_expected"].lower()
    assert blocked["raw_visibility"] == "hidden_by_default"
