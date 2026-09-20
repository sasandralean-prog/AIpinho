from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


class _FakeWorkspaceFixDiscoveryService:
    def execute(self, **_kwargs):
        return SimpleNamespace(
            run=SimpleNamespace(
                task_id="task_fix_discovery",
                run_id="task_run_fix_discovery",
                mission_binding=SimpleNamespace(
                    mission_id="mission_fix_discovery",
                    authority_sha256="authority_fix_discovery",
                ),
            ),
            result=SimpleNamespace(
                status="completed",
                reason_code=None,
                warnings=[],
                trace_ref="trace_fix_discovery",
            ),
        )


def _fix_mission_chat_service() -> CanonicalPublicChatService:
    return CanonicalPublicChatService(
        workspace_fix_discovery=_FakeWorkspaceFixDiscoveryService()
    )


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
    response = _fix_mission_chat_service().respond(
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

def test_embedded_authorization_does_not_replace_operational_patch_intent() -> None:
    prompt = (
        "Autorizo nesta missao leitura, diagnostico, edicao de codigo, criacao de testes, "
        "execucao de Gradle build e git push. "
        r"WORKSPACE DO APP: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        r"CORPUS SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Nao modifique o corpus. Corrija o pipeline de codec no workspace, edite o codigo, "
        "adicione testes, execute o build, valide e depois faca commit e push. "
        "Nao versione build, caches ou artefatos transitorios."
    )

    decision = SemanticIntentResolutionService().resolve(prompt, source_channel="unit")

    assert decision.intent_type == "patch_or_write_request"
    assert decision.operation_type == "patch_request"
    assert decision.requires_task is True
    assert decision.side_effect_requested is True
    assert decision.readonly is False
    assert "positive_permission_grant_signal" not in decision.evidence


def test_long_operational_prompt_prefers_labeled_workspace_over_later_corpus_path() -> None:
    prompt = (
        r"WORKSPACE DO APP A SER CORRIGIDO: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        r"CORPUS DE MUSICAS PARA TESTES - SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Corrija o player no workspace e nao modifique o corpus."
    )
    service = CanonicalPublicChatService()
    workspace = service._workspace_from_request(ChatRequest(message=prompt, session_id="unit_session"))

    assert workspace == r"C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop"

def test_scoped_readonly_path_preserves_mutable_target_semantics() -> None:
    prompt = (
        r"WORKSPACE ALVO: C:\Work\TargetApp. "
        r"CORPUS SOMENTE LEITURA: D:\Media\ReadonlyCorpus. "
        r"Nao modifique D:\Media\ReadonlyCorpus. "
        "Edite e corrija o codigo no workspace alvo, execute testes e build."
    )

    decision = SemanticIntentResolutionService().resolve(
        prompt,
        source_channel="unit",
        workspace_hint=r"C:\Work\TargetApp",
    )

    assert decision.semantic_intent_graph.mutation_intent is True
    assert (
        "workspace_mutation"
        not in decision.semantic_intent_graph.prohibited_effects
    )
    assert decision.semantic_intent_graph.filesystem_effect == "mutable"

    by_locator = {
        item.locator: item
        for item in decision.local_resources
        if item.locator
    }
    target = by_locator[r"C:\Work\TargetApp"]
    corpus = by_locator[r"D:\Media\ReadonlyCorpus"]

    assert target.role == "target_mutable"
    assert "modify_file" in target.permissions
    assert corpus.role == "source_readonly"
    assert "read_file" in corpus.permissions
    assert "modify_file" not in corpus.permissions
    assert "apply_patch" not in corpus.permissions


def test_generic_investigate_and_repair_mission_is_discovery_first() -> None:
    decision = SemanticIntentResolutionService().resolve(
        "Investigue e corrija estruturalmente o aplicativo no workspace. Depois execute testes e build.",
        source_channel="unit",
    )

    assert decision.intent_type == "workspace_fix_request"
    assert decision.operation_type == "workspace_fix_request"
    assert decision.readonly is True
    assert decision.side_effect_requested is False
    assert decision.semantic_intent_graph.mutation_intent is True
    assert decision.semantic_intent_graph.execution_intent is True
    assert "future_side_effect_intent_deferred_until_discovery" in decision.evidence


def test_public_chat_long_authorized_mission_is_not_session_diagnostic() -> None:
    prompt = (
        "Autorizo nesta missao leitura, diagnostico, edicao de codigo, criacao de testes, "
        "execucao de Gradle build e git push. "
        r"WORKSPACE DO APP A SER CORRIGIDO: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        r"CORPUS DE MUSICAS PARA TESTES - SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Nao modifique o corpus. Investigue e corrija os problemas de codec no workspace. "
        "Adicione testes, execute o build, valide, faca commit e git push. "
        "Nao versione build, caches ou artefatos transitorios."
    )

    response = _fix_mission_chat_service().respond(
        ChatRequest(message=prompt, session_id="unit_long_mission"),
        source_channel="mobile_chat",
    )

    assert response.operation_type == "workspace_fix_request"
    assert response.intent["intent_type"] == "workspace_fix_request"
    assert response.governance_lifecycle["intent"]["requires_task"] is True
    assert response.governance_lifecycle["operation_contract"]["workspace_path"] == r"C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop"
    assert response.governance_lifecycle["operation_contract"]["read_only"] is True
    assert response.governance_lifecycle["operation_contract"]["workspace_mutation"] is False
    assert response.governance_lifecycle["operation_contract"]["requested_actions"] == []
    assert "future_side_effect_intent_deferred_until_discovery" in response.governance_lifecycle["intent"]["evidence"]
    assert response.task_run_id == "task_run_fix_discovery"
    assert response.status == "ok"
    assert "WORKSPACE_FIX_DISCOVERY_COMPLETED" in response.message

def test_subdirectory_word_does_not_convert_patch_mission_to_create_directory() -> None:
    prompt = (
        "Autorizo edicao de codigo, testes, build e git push. "
        r"WORKSPACE DO APP A SER CORRIGIDO: C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop. "
        "O workspace local corresponde ao subdiretorio PinhoabacaxiMusicasDesktop/ do repositorio canonico. "
        r"CORPUS SOMENTE LEITURA: D:\rafa\novapinhomusic. "
        "Nao modifique o corpus. Investigue e corrija os problemas de codec no workspace. "
        "Execute o build, valide, faca commit e git push."
    )
    service = _fix_mission_chat_service()
    response = service.respond(ChatRequest(message=prompt, session_id="unit_subdir_patch"), source_channel="mobile_chat")

    assert response.operation_type == "workspace_fix_request"
    assert response.governance_lifecycle["operation_contract"]["operation_type"] == "workspace_fix_request"
    assert response.governance_lifecycle["operation_contract"]["requested_actions"] == []
    assert response.governance_lifecycle["intent"]["negative_constraints"].get("write_forbidden") is not True
    assert response.governance_lifecycle["intent"]["negative_constraints"].get("shell_forbidden") is not True


class _BlockedContinuationDiscoveryService:
    def execute(self, **_kwargs):
        return SimpleNamespace(
            run=SimpleNamespace(
                task_id="task_fix_blocked",
                run_id="task_run_fix_blocked",
                current_phase="discovery",
                mission_binding=SimpleNamespace(
                    mission_id="mission_fix_blocked",
                    authority_sha256="authority_fix_blocked",
                ),
                intent_map={
                    "mission_continuation_runtime": {
                        "status": "blocked",
                        "reason_code": "mission_continuation_phase_outcome_missing",
                        "candidate_id": "candidate_fix_blocked",
                        "child_task_run_id": None,
                        "child_status": None,
                        "decision_action": "block",
                        "next_phase": None,
                    }
                },
                plan=SimpleNamespace(metadata={}),
            ),
            result=SimpleNamespace(
                status="partial",
                reason_code="task_run_partial",
                warnings=[],
                trace_ref="trace_fix_blocked",
            ),
        )


def test_public_fix_response_projects_runtime_continuation_block() -> None:
    service = CanonicalPublicChatService(
        workspace_fix_discovery=_BlockedContinuationDiscoveryService()
    )
    prompt = (
        "Investigue e corrija estruturalmente o aplicativo. "
        r"WORKSPACE DO APP A SER CORRIGIDO: C:\Work\TargetApp. "
        "Autorizo edicao, testes, build, commit e push."
    )

    response = service.respond(
        ChatRequest(message=prompt, session_id="unit_continuation_block"),
        source_channel="mobile_chat",
    )

    assert response.status == "blocked"
    assert (
        response.policy["reason_code"]
        == "mission_continuation_phase_outcome_missing"
    )
    assert response.contract_preview["phase"] == "discovery"
    assert response.contract_preview["continuation_status"] == "blocked"
    assert response.contract_preview["next_phase"] is None
    assert "continuation_owner" not in response.contract_preview
