from __future__ import annotations

from pathlib import Path

from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.services.semantic_runtime.semantic_interpreter_pipeline import SemanticInterpreterPipeline, SemanticInterpreterRole


def test_semantic_interpreter_produces_isr_without_side_effects():
    result = SemanticInterpreterPipeline().run(
        r'Diagnostique em modo read-only o workspace "C:\Users\rafae\Documents\TestesIALocal\SapoAndando". '
        "Nao modificar, nao criar artifact, nao executar shell."
    )

    output = result.output
    assert result.status == "ready"
    assert output.intent == "readonly_analysis"
    assert output.scope == "workspace_or_filesystem"
    assert output.constraints["read_only"] is True
    assert output.constraints["no_shell"] is True
    assert output.side_effects is False
    assert output.created_contract is False
    assert output.runtime_executed is False
    assert output.tools_called is False
    assert output.skills_called is False
    assert output.files_written is False
    assert output.patches_created is False
    assert output.task_id is None
    assert output.approval_id is None


def test_semantic_interpreter_is_stable_and_repeatable():
    prompt = "Crie um plano textual para revisar arquitetura, mas nao execute nada."
    first = SemanticInterpreterPipeline().run(prompt).output
    second = SemanticInterpreterPipeline().run(prompt).output

    assert first.intent == second.intent
    assert first.scope == second.scope
    assert first.constraints == second.constraints
    assert first.requested_outputs == second.requested_outputs
    assert first.confidence == second.confidence
    assert first.ambiguity_score == second.ambiguity_score


def test_semantic_interpreter_uses_capability_registry():
    output = SemanticInterpreterPipeline().run("Explique sua arquitetura em texto.").output

    assert output.capability_id == "semantic_understanding"
    assert output.model_selection["capability_id"] == "semantic_understanding"
    assert output.model_selection["role_id"] == "semantic_interpreter"
    assert output.model_selection["selected_model_id"] == "qwen3_1_7b_q6_k"


def test_semantic_interpreter_feature_flag_disables_parallel_isr(tmp_path: Path):
    config_path = tmp_path / "semantic_interpreter.yaml"
    config_path.write_text(
        """
schema_version: 1
semantic_runtime:
  semantic_runtime_enabled: false
semantic_interpreter:
  role_id: semantic_interpreter
  capability: semantic_understanding
""",
        encoding="utf-8",
    )
    role = SemanticInterpreterRole(config_path=config_path)

    result = SemanticInterpreterPipeline(role=role).run("Analise este texto.")

    assert result.status == "disabled"
    assert result.output.blocked_reasons == ["semantic_runtime_disabled"]
    assert result.output.runtime_executed is False


def test_semantic_interpreter_runs_parallel_to_current_intent_map():
    prompt = "Pesquise na internet noticias recentes sobre Android Studio."
    current_intent = PromptIntelligenceService().analyze(type("Req", (), {"prompt": prompt, "context": {}})()).intent_map
    semantic_output = SemanticInterpreterPipeline().run(prompt).output

    assert current_intent.intent_id.startswith("intent_")
    assert semantic_output.isr_id.startswith("isr_")
    assert semantic_output.task_id is None
    assert semantic_output.approval_id is None
    assert semantic_output.intent in {"public_fact_query", "unknown", "conversation"}
