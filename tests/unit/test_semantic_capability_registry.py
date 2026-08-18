from __future__ import annotations

from pathlib import Path

from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_model_gate_service_v2 import RoleModelGateServiceV2
from aipinho.services.semantic_runtime.capability_resolver import CapabilityResolver
from aipinho.services.semantic_runtime.semantic_capability_registry import SemanticCapabilityRegistry


def _write_registry(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_capability_registry_loads_contracts_and_role_bindings():
    registry = SemanticCapabilityRegistry()

    assert "code_generation" in registry.contracts
    assert registry.get_role_binding("coder") is not None
    assert registry.get_role_binding("coder").capability_id == "code_generation"  # type: ignore[union-attr]


def test_fallback_selection_uses_registry_when_primary_unavailable(tmp_path: Path):
    config_path = tmp_path / "capability_registry.yaml"
    _write_registry(
        config_path,
        """
schema_version: 1
capabilities:
  code_generation:
    display_name: CodeGeneration
    enabled: true
    aliases: [code]
    primary_model: missing_model
    fallback_models: [qwen2_5_coder_1_5b_q8_0]
role_capability_bindings:
  test_coder:
    capability: code_generation
    primary: missing_model
    fallback: qwen2_5_coder_1_5b_q8_0
""",
    )
    resolver = CapabilityResolver(registry=SemanticCapabilityRegistry(config_path=config_path))

    selection = resolver.resolve_for_role("test_coder")

    assert selection.allowed is True
    assert selection.status == "fallback"
    assert selection.selected_model_id == "qwen2_5_coder_1_5b_q8_0"
    assert "model_not_registered" in selection.warnings


def test_disabled_capability_blocks_selection(tmp_path: Path):
    config_path = tmp_path / "capability_registry.yaml"
    _write_registry(
        config_path,
        """
schema_version: 1
capabilities:
  embedding:
    display_name: Embedding
    enabled: false
    aliases: [embedding]
    primary_model: qwen3_embedding_4b_q5_k_m
role_capability_bindings:
  embedder:
    capability: embedding
    primary: qwen3_embedding_4b_q5_k_m
""",
    )
    resolver = CapabilityResolver(registry=SemanticCapabilityRegistry(config_path=config_path))

    selection = resolver.resolve_for_role("embedder")

    assert selection.allowed is False
    assert selection.status == "disabled"
    assert "capability_disabled" in selection.blocked_reasons


def test_escalation_selection_uses_escalation_candidate():
    selection = CapabilityResolver().resolve_for_role("planner", manual=True)

    assert selection.allowed is True
    assert selection.status == "escalation"
    assert selection.selected_model_id == "deepseek_r1_distill_qwen_14b_q4_k_m"


def test_role_model_gate_v2_uses_capability_registry_for_coder():
    decision = RoleModelGateServiceV2().decide("coder", RoleInferenceRequest(role_id="coder", prompt="implemente uma funcao"))

    assert decision.allowed is True
    assert decision.capability_id == "code_generation"
    assert decision.selection_source == "primary"
    assert decision.selected_model_id == "qwen2_5_coder_7b_q4_k_m"
