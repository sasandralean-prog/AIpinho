from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


def test_readonly_constraints_override_write_patch_and_shell_signals() -> None:
    decision = SemanticIntentResolutionService().resolve(
        r'Diagnostico read-only do workspace "C:\Users\rafae\Documents\TestesIALocal\SapoAndando". '
        "Nao modificar arquivos. Nao criar artifact. Nao rodar patch. "
        "Nao executar build. Gere apenas diagnostico e preview textual futuro.",
        source_channel="unit",
    )

    assert decision.readonly is True
    assert decision.side_effect_requested is False
    assert decision.intent_type == "workspace_analysis_readonly"
    assert decision.operation_type == "workspace_analysis_readonly"
    assert decision.negative_constraints["write_forbidden"] is True
    assert decision.negative_constraints["patch_forbidden"] is True
    assert decision.negative_constraints["artifact_forbidden"] is True


def test_conditional_safety_constraints_do_not_turn_patch_request_into_readonly() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Aplicar exclusivamente o plano aprovado. "
        "Nao modificar nada sem plano executavel aprovado, approval valido, rollback e validacao. "
        "Gerar diff completo, arquivos alterados, build e logs.",
        source_channel="unit",
    )

    assert decision.intent_type == "patch_or_write_request"
    assert decision.operation_type == "patch_request"
    assert decision.requires_task is True
    assert decision.side_effect_requested is True
    assert decision.readonly is False
    assert decision.negative_constraints["write_forbidden"] is True
    assert "negative_constraints_preserved" in decision.evidence


def test_readonly_fix_explanation_remains_readonly_even_with_correction_words() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Analise o workspace em modo somente leitura. "
        "Nao modificar arquivos. Explique como corrigir os problemas em um relatorio.",
        source_channel="unit",
    )

    assert decision.intent_type == "workspace_analysis_readonly"
    assert decision.operation_type == "workspace_analysis_readonly"
    assert decision.readonly is True
    assert decision.side_effect_requested is False


def test_positive_permission_grant_becomes_semantic_permission_request() -> None:
    decision = SemanticIntentResolutionService().resolve(
        r"Dou permissao para escrever e criar arquivos durante esta tarefa em C:\Work\App.",
        source_channel="unit",
    )

    assert decision.intent_type == "permission_grant_request"
    assert decision.operation_type == "session_permission_grant"
    assert decision.requires_task is False
    assert decision.side_effect_requested is False


def test_readonly_permission_wording_does_not_become_permission_grant() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Isto NAO e pedido para criar grant. Nao escrever arquivos. Classifique como product_planning_readonly.",
        source_channel="unit",
    )

    assert decision.intent_type == "product_planning_readonly"
    assert decision.readonly is True
    assert decision.negative_constraints["write_forbidden"] is True


def test_explicit_shell_request_routes_to_governed_shell() -> None:
    decision = SemanticIntentResolutionService().resolve(
        r'Execute "npm test" em "C:\Work\App".',
        source_channel="unit",
    )

    assert decision.intent_type == "governed_shell_request"
    assert decision.operation_type == "run_command"
    assert decision.requires_task is True
    assert decision.side_effect_requested is True


def test_public_chat_preserves_canonical_patch_intent_for_conditional_execution_request() -> None:
    response = CanonicalPublicChatService().respond(
        ChatRequest(
            message=(
                "Aplicar exclusivamente o plano aprovado. "
                "Nao modificar nada sem plano executavel aprovado, approval valido, rollback e validacao. "
                "Gerar diff completo, arquivos alterados, build e logs."
            ),
            session_id="unit_session",
        ),
        source_channel="unit",
    )

    assert response.intent["intent_type"] == "patch_or_write_request"
    assert response.operation_type == "patch_request"
    assert response.actions == ["apply_patch"]
    assert response.approval_id is None
    assert response.status == "preview"
    assert response.governance_lifecycle["completion"]["safe_to_report_success"] is False
    assert response.governance_lifecycle["speaker_truth"]["can_claim_success"] is False


def test_public_chat_artifact_expectations_do_not_override_executable_patch_intent() -> None:
    response = CanonicalPublicChatService().respond(
        ChatRequest(
            message=(
                "Aplicar exclusivamente o plano aprovado produzido pela etapa de planejamento. "
                "Nao modificar nada sem plano executavel aprovado. "
                "Nao executar patch se faltar target real, diff completo, rollback definido, "
                "validation plan ou approval valido. "
                "Gerar diff completo, arquivos alterados, build, logs. "
                "Artifacts obrigatorios: reports/runtime/patch.md reports/runtime/build_report.md"
            ),
            session_id="unit_session",
        ),
        source_channel="unit",
    )

    assert response.intent["intent_type"] == "patch_or_write_request"
    assert response.operation_type == "patch_request"
    assert response.actions == ["apply_patch"]
    assert response.approval_id is None
    assert response.status == "preview"
    assert response.governance_lifecycle["completion"]["status"] == "incomplete"
    assert response.governance_lifecycle["completion"]["safe_to_report_success"] is False


def test_negative_patch_and_build_language_preserves_readonly_discovery() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Discovery completo do projeto em modo somente leitura. "
        "Nao gerar patch. Nao executar build. Gerar relatorio em reports/phase1.md.",
        source_channel="unit",
    )

    assert decision.intent_type == "workspace_analysis_readonly"
    assert decision.operation_type == "workspace_analysis_readonly"
    assert decision.readonly is True
    assert decision.side_effect_requested is False


def test_proposal_artifacts_with_write_prohibition_do_not_promote_to_patch_request() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Utilizar evidencias anteriores. Ainda nao modificar codigo. "
        "Responder causa raiz, estrategia, riscos e rollback. "
        "Artifacts reports/phase4_patch_plan.md, reports/patch_preview.md e reports/risk_analysis.md.",
        source_channel="unit",
    )

    assert decision.intent_type == "workspace_analysis_readonly"
    assert decision.operation_type == "workspace_analysis_readonly"
    assert decision.readonly is True
    assert decision.side_effect_requested is False
    assert decision.semantic_intent_graph.state_effect == "proposal_only"
