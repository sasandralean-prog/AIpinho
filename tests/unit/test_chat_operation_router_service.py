from __future__ import annotations

from aipinho.services.chat.chat_operation_router_service import ChatOperationRouterService


def test_artifact_request_routes_to_offer_without_final_answer_contract() -> None:
    decision = ChatOperationRouterService().route("Crie um zip com um arquivo de resposta para baixar.")

    assert decision.operation_type == "artifact_generation"
    assert decision.metadata["router_operation_type"] == "artifact_request"
    assert decision.message_type == "artifact_offer"
    assert decision.primary_prompt
    assert decision.metadata["requested_output"]["artifact_requested"] is True


def test_readonly_project_analysis_with_artifact_keeps_analysis_as_primary_intent() -> None:
    decision = ChatOperationRouterService().route(
        r'Analise o projeto "C:\Projeto Exemplo" e gere um pacote.zip com relatorio.txt para download.',
    )

    assert decision.operation_type == "report_generation"
    assert decision.metadata["router_operation_type"] == "readonly_analysis_with_artifact_output"
    assert decision.message_type == "assistant_final_answer"
    assert decision.workspace == r"C:\Projeto Exemplo"
    assert decision.metadata["requested_output"]["artifact_requested"] is True
    assert decision.metadata["requested_output"]["filenames"]["package"] == "pacote.zip"
    assert decision.metadata["requested_output"]["filenames"]["text"] == "relatorio.txt"
    assert decision.metadata["output_target"] == "artifact_store"
    assert decision.metadata["workspace_write"] is False


def test_explicit_workspace_output_is_not_misclassified_as_external_artifact() -> None:
    decision = ChatOperationRouterService().route(
        r"Salve pacote.zip dentro da pasta C:\Example\Source.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "workspace_artifact_write_request"
    assert decision.message_type == "artifact_preview"
    assert decision.metadata["output_target"] == "workspace"
    assert decision.metadata["workspace_write"] is True


def test_readonly_project_path_routes_to_task_preview() -> None:
    decision = ChatOperationRouterService().route(r"Analise o projeto C:\ProjetoExemplo sem alterar arquivos.")

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"
    assert decision.message_type == "task_preview"
    assert decision.workspace == r"C:\ProjetoExemplo"


def test_quoted_workspace_can_keep_spaces_without_leaking_constraints() -> None:
    decision = ChatOperationRouterService().route(r'Analise o projeto "C:\Projeto Exemplo" sem alterar arquivos.')

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"
    assert decision.workspace == r"C:\Projeto Exemplo"


def test_windows_workspace_with_forward_separators_is_normalized() -> None:
    decision = ChatOperationRouterService().route(
        "Analise o projeto C:/Workspaces/ProjetoExemplo sem alterar arquivos.",
    )

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"
    assert decision.workspace == r"C:\Workspaces\ProjetoExemplo"


def test_session_diagnostic_routes_before_llm() -> None:
    decision = ChatOperationRouterService().route("Diagnostique o bug na timeline da conversa truncada.")

    assert decision.operation_type == "session_diagnostic"
    assert decision.message_type == "system_diagnostic_result"


def test_start_project_prompt_routes_to_project_bootstrap_not_session_diagnostic() -> None:
    decision = ChatOperationRouterService().route("AIpinho - Iniciar Projeto AIpinho Studio com governanca completa")

    assert decision.operation_type != "session_diagnostic"
    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "project_bootstrap"
    assert decision.metadata["requires_task"] is True
    assert decision.metadata["requested_operation"] == "project_bootstrap"


def test_session_diagnostic_only_when_explicit() -> None:
    diagnostic = ChatOperationRouterService().route("diagnostique esta sessao")
    operational = ChatOperationRouterService().route("Iniciar projeto com safety check e diagnostico de approval")

    assert diagnostic.operation_type == "session_diagnostic"
    assert operational.operation_type != "session_diagnostic"
    assert operational.metadata["router_operation_type"] == "project_bootstrap"


def test_safety_check_section_does_not_hijack_project_prompt() -> None:
    decision = ChatOperationRouterService().route(
        """
        Iniciar Projeto AIpinho Studio.
        FASE 0 - SAFETY CHECK DO HOTFIX
        Diagnostico de approval e preview antes de escrever.
        """
    )

    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "project_bootstrap"
    assert decision.metadata["safety_check_as_internal_step"] is True


def test_workspace_audit_report_routes_before_session_diagnostic() -> None:
    decision = ChatOperationRouterService().route(
        r"""
        Investigue os testes E2E historicos que ainda esperam:
        1. C:\PinhoabacaxiAI como forbidden;
        2. real_inference globalmente bloqueada.
        Nao altere codigo nesta tarefa.
        Gere relatorio em reports/audit.md.
        """,
        workspace_hint=r"C:\Dev\AIpinho",
    )

    assert decision.operation_type == "workspace_readonly_audit_report"
    assert decision.metadata["router_operation_type"] == "workspace_readonly_audit_report"
    assert decision.metadata["report_relative_path"] == "reports/audit.md"
    assert "real_inference" in decision.metadata["search_terms"]
    assert decision.message_type == "task_status_update"


def test_correction_plan_report_without_apply_routes_to_readonly_audit_report() -> None:
    decision = ChatOperationRouterService().route(
        """
        Prepare um plano de correcao minimo para fazer o APK abrir sem erro.
        Nao aplique patch nesta fase.
        Liste arquivos candidatos, comandos candidatos, validation plan e rollback plan.
        Gere o plano em reports/aipinho_firetest4_correction_plan.md.
        """,
        workspace_hint=r"C:\WorkspaceAlvo",
    )

    assert decision.operation_type == "workspace_readonly_audit_report"
    assert decision.metadata["router_operation_type"] == "workspace_readonly_audit_report"
    assert decision.metadata["report_relative_path"] == "reports/aipinho_firetest4_correction_plan.md"


def test_report_output_path_wins_over_source_report_references() -> None:
    decision = ChatOperationRouterService().route(
        """
        Baseie-se nos relatorios:
        - reports/preflight.md
        - reports/runtime_diagnosis.md

        Prepare um plano de correcao minimo.
        Nao aplique patch nesta fase.
        Gere o plano em reports/correction_plan.md.
        """,
        workspace_hint=r"C:\WorkspaceAlvo",
    )

    assert decision.operation_type == "workspace_readonly_audit_report"
    assert decision.metadata["report_relative_path"] == "reports/correction_plan.md"


def test_regenerate_report_uses_configured_readonly_audit_terms() -> None:
    decision = ChatOperationRouterService().route(
        """
        Regenere o plano de correcao minimo.
        Nao aplique patch nesta fase.
        Gere o plano em reports/correction_plan.md.
        """,
        workspace_hint=r"C:\WorkspaceAlvo",
    )

    assert decision.operation_type == "workspace_readonly_audit_report"
    assert decision.metadata["report_relative_path"] == "reports/correction_plan.md"


def test_project_persistence_diagnosis_is_not_session_diagnostic() -> None:
    decision = ChatOperationRouterService().route(
        "Investigue a persistencia do projeto e gere relatorio em reports/persistence_diagnosis.md. Nao corrija ainda.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "create_file"


def test_implementation_with_report_target_routes_to_governed_task_not_report_write() -> None:
    decision = ChatOperationRouterService().route(
        "Com base no diagnostico anterior, implemente uma correcao minima para a persistencia. "
        "Rode test/build/check e gere relatorio em reports/persistence_fix.md.",
        workspace_hint=r"C:\WorkspaceAlvo",
    )

    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.metadata["requires_patch_preview"] is True


def test_registered_workspace_listing_routes_to_permission_status() -> None:
    decision = ChatOperationRouterService().route("Liste os workspaces registrados.")

    assert decision.operation_type == "workspace_permission_list"
    assert decision.workspace is None


def test_permission_status_routes_without_workspace_requirement() -> None:
    decision = ChatOperationRouterService().route(
        "Liste os diretorios que tenho permissao para ler, escrever, gerar artifact e usar shell governado.",
    )

    assert decision.operation_type == "permission_status"
    assert decision.message_type == "assistant_final_answer"
    assert decision.workspace is None


def test_list_approved_workspaces_routes_to_workspace_permission_list() -> None:
    decision = ChatOperationRouterService().route("pode listar os workspaces aprovados para escrita?")

    assert decision.operation_type == "workspace_permission_list"
    assert decision.message_type == "assistant_final_answer"
    assert decision.metadata["requires_task"] is False


def test_permission_status_tolerates_small_target_typo_without_exact_prompt_rule() -> None:
    decision = ChatOperationRouterService().route(
        "Pode listar os diretorios com leitura e ewcrita permitidas?",
    )

    assert decision.operation_type == "permission_status"


def test_permission_status_does_not_capture_operational_prompt_with_permission_report_section() -> None:
    decision = ChatOperationRouterService().route(
        r"Analise o projeto C:\ProjetoExemplo em modo read-only. Antes de qualquer escrita, gere um plano com riscos, policy e permissoes necessarias.",
    )

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"


def test_product_planning_readonly_routes_before_config_or_grant_language() -> None:
    decision = ChatOperationRouterService().route(
        """
        AIpinho - Fase 0A do Projeto AIpinho Studio Mobile: somente planejamento textual.
        Objetivo: responder somente com analise de produto, relatorio e plano de acao em 5 sprints.
        Isto NAO e pedido para criar grant, NAO e escrita, NAO e shell, NAO e ConfigChangeRequest.
        Classifique este pedido como: product_planning_readonly.
        """
    )

    assert decision.operation_type == "product_planning_readonly"
    assert decision.metadata["requires_task"] is False
    assert decision.metadata["approval_required"] is False
    assert decision.metadata["write_allowed"] is False


def test_chat_only_workspace_metadata_query_does_not_become_file_write() -> None:
    decision = ChatOperationRouterService().route(
        r"""
        Leia apenas metadados do workspace: "C:\ProjetoExemplo"
        Nao crie arquivo.
        Nao gere relatorio.
        Responda somente no chat:
        1. existe build.gradle?
        2. existe package.json?
        3. quais arquivos de entrada parecem existir?
        """,
    )

    assert decision.operation_type == "workspace_metadata_query"
    assert decision.message_type == "assistant_final_answer"
    assert decision.metadata["workspace_write"] is False
    assert decision.metadata["read_only"] is True
    assert decision.metadata["chat_only"] is True
    assert decision.metadata["requested_files"] == ["build.gradle", "package.json"]


def test_prompt_requested_policy_workspace_config_change_routes_to_governed_preview() -> None:
    decision = ChatOperationRouterService().route(
        "Configure as policies e workspaces para permitir escrita governada com approval.",
    )

    assert decision.operation_type == "governed_configuration_change"
    assert decision.message_type == "task_preview"
    assert decision.metadata["router_operation_type"] == "governed_configuration_change"
    assert decision.metadata["direct_mutation_allowed"] is False
    assert {"policy", "workspace"}.issubset(set(decision.metadata["configuration_targets"]))


def test_report_fields_do_not_turn_readonly_analysis_into_artifact_request() -> None:
    decision = ChatOperationRouterService().route(
        r"Analise C:\ProjetoExemplo em read-only e gere um relatório com arquivos analisados, traces, events e artifacts. Não altere arquivos.",
    )

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"
    assert decision.metadata.get("artifact_generation") is None


def test_permission_status_still_accepts_direct_permission_question() -> None:
    decision = ChatOperationRouterService().route(
        r"Quais permissoes tenho para o workspace C:\ProjetoExemplo?",
    )

    assert decision.operation_type == "permission_status"


def test_simple_conversation_stays_final_answer() -> None:
    decision = ChatOperationRouterService().route("Bom dia, tudo certo?")

    assert decision.operation_type == "conversation"
    assert decision.metadata["router_operation_type"] == "simple_conversation"
    assert decision.message_type == "assistant_final_answer"


def test_followup_summary_is_classified_separately_from_answer_recall() -> None:
    decision = ChatOperationRouterService().route("Pode repetir o resumo?")

    assert decision.operation_type == "followup_result_recall"
    assert decision.metadata["recall_kind"] == "summary"


def test_followup_answer_keeps_general_answer_recall() -> None:
    decision = ChatOperationRouterService().route("Repita a resposta anterior.")

    assert decision.operation_type == "followup_result_recall"
    assert decision.metadata["recall_kind"] == "answer"


def test_followup_review_of_previous_plan_does_not_become_patch_request() -> None:
    decision = ChatOperationRouterService().route(
        "Faca uma revisao automatica do planejamento anterior antes de executar.",
    )

    assert decision.operation_type == "followup_result_review"
    assert decision.message_type == "assistant_final_answer"
    assert decision.workspace is None
    assert decision.metadata["recall_kind"] == "summary"


def test_governed_project_rebuild_routes_to_task_preview_before_patch_quality_fallback() -> None:
    decision = ChatOperationRouterService().route(
        r"Execute o proximo sprint apenas dentro do workspace alvo C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo. Gere preview antes de escrita, peca approval e rode validacao.",
    )

    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.message_type == "task_preview"
    assert decision.workspace == r"C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo"
    assert decision.metadata["requires_patch_preview"] is True


def test_simple_governed_file_write_routes_before_project_rebuild() -> None:
    decision = ChatOperationRouterService().route(
        r"Crie no workspace alvo C:\Users\rafae\Documents\AIpinhoTestes um arquivo README_TESTE.md com conteudo 'teste de escrita governada'.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.message_type == "task_status_update"
    assert decision.workspace == r"C:\Users\rafae\Documents\AIpinhoTestes"
    assert decision.metadata["requested_operation"] == "create_file"


def test_governed_shell_request_routes_before_build_or_project_generation() -> None:
    decision = ChatOperationRouterService().route(
        r"Rode npm test no workspace C:\Users\rafae\Documents\AIpinhoTestes.",
    )

    assert decision.operation_type == "shell_execute"
    assert decision.metadata["router_operation_type"] == "governed_shell_request"
    assert decision.message_type == "task_status_update"
    assert decision.metadata["requested_operation"] == "run_command"
    assert decision.metadata["requested_actions"] == ["run_command"]
    assert decision.metadata["approval_scope"] == "governed_shell"


def test_chat_operation_router_records_semantic_shell_resolution() -> None:
    decision = ChatOperationRouterService().route(r'Execute "npm test" em "C:\Work\App".')

    assert decision.operation_type == "shell_execute"
    assert decision.metadata["router_operation_type"] == "governed_shell_request"
    assert decision.metadata["semantic_intent"]["intent_type"] == "governed_shell_request"


def test_report_generation_with_negative_modify_constraint_stays_create_file() -> None:
    decision = ChatOperationRouterService().route(
        "Analise o projeto em modo read-only e gere um relatorio em reports/project_scan.md. Nao altere codigo nesta tarefa.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "create_file"


def test_additive_instruction_targeting_existing_file_routes_to_modify() -> None:
    decision = ChatOperationRouterService().route("Adicione ao README.md uma secao curta de validacao.")

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "modify_file"


def test_visible_ui_text_update_routes_to_governed_modify_before_build_validation() -> None:
    decision = ChatOperationRouterService().route(
        'Implemente uma pequena melhoria de UX: adicione o texto visivel "Sistema pronto" na tela principal do app. Valide que o texto aparece em algum arquivo fonte.',
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "modify_file"
    assert decision.metadata["target_resolution"] == "infer_ui_source"


def test_status_text_ui_update_routes_to_governed_modify() -> None:
    decision = ChatOperationRouterService().route(
        'Adicionar no dashboard ou tela principal um texto discreto de status: "Sistema pronto". Rode validacao disponivel.',
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "modify_file"
    assert decision.metadata["target_resolution"] == "infer_ui_source"


def test_negative_destructive_constraint_does_not_block_safe_readme_update() -> None:
    decision = ChatOperationRouterService().route(
        'Atualize o README.md adicionando uma secao "Firetest AIpinho". Nao remova conteudo existente.',
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.metadata["requested_operation"] == "modify_file"


def test_governed_modify_file_routes_as_governed_write_not_patch() -> None:
    decision = ChatOperationRouterService().route(
        "Modifique o arquivo README_EXISTENTE.md no workspace alvo adicionando uma secao de validacao.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.metadata["router_operation_type"] == "governed_file_write"
    assert decision.message_type == "task_status_update"
    assert decision.metadata["requested_operation"] == "modify_file"


def test_readonly_analysis_accepts_generic_source_project_term() -> None:
    decision = ChatOperationRouterService().route(
        "Analise o source_readonly_project em modo somente leitura. Gere um relatorio markdown com riscos. Nao altere arquivos.",
    )

    assert decision.operation_type == "project_analysis"
    assert decision.metadata["router_operation_type"] == "readonly_project_analysis"
    assert decision.message_type == "task_preview"


def test_governed_project_rebuild_routes_corrective_preview_to_task_preview() -> None:
    decision = ChatOperationRouterService().route(
        r"Gere um novo preview governado para sincronizar o workspace alvo C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo. Use approval e validation, sem escrita direta.",
    )

    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.message_type == "task_preview"
    assert decision.workspace == r"C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo"
    assert decision.metadata["requires_patch_preview"] is True


def test_governed_change_plan_treats_referenced_report_as_evidence_not_write_target() -> None:
    decision = ChatOperationRouterService().route(
        r"Com base no plano em reports\correction_plan.md, gere preview e plano de correcao no workspace C:\Users\rafae\Documents\AIpinhoTestes\Projeto. Ainda nao aplique.",
    )

    assert decision.operation_type == "patch_preview"
    assert decision.metadata["router_operation_type"] == "governed_change_plan"
    assert decision.message_type == "task_preview"
    assert decision.workspace == r"C:\Users\rafae\Documents\AIpinhoTestes\Projeto"
    assert decision.metadata["referenced_files_role"] == "evidence_source"
    assert decision.metadata["workspace_write"] is False


def test_governed_change_plan_requires_explicit_deferred_apply() -> None:
    decision = ChatOperationRouterService().route(
        r"Modifique o arquivo reports\correction_plan.md no workspace C:\Users\rafae\Documents\AIpinhoTestes\Projeto.",
    )

    assert decision.metadata["router_operation_type"] == "governed_file_write"


def test_session_execution_report_routes_before_patch_quality_fallback() -> None:
    decision = ChatOperationRouterService().route(
        "Gere um relatorio final honesto da execucao supervisionada com apply, approval, validation, riscos e arquivos criados. Nao altere arquivos.",
    )

    assert decision.operation_type == "report_generation"
    assert decision.metadata["router_operation_type"] == "session_execution_report"
    assert decision.message_type == "assistant_final_answer"
    assert decision.workspace is None


def test_session_execution_report_does_not_hijack_new_workspace_operation() -> None:
    decision = ChatOperationRouterService().route(
        r"No workspace C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo, gere wrapper limpo, compile e depois retorne um relatorio honesto.",
    )

    assert decision.operation_type != "session_execution_report"
    assert decision.workspace == r"C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo"


def test_operational_create_directory_does_not_fall_back_to_simple_conversation() -> None:
    decision = ChatOperationRouterService().route(
        r"Crie uma pasta em C:\Users\rafae\Documents\TestesIALocal\NovaPasta.",
    )

    assert decision.operation_type == "filesystem_create_directory"
    assert decision.message_type == "task_status_update"
    assert decision.metadata["approval_scope"] == "filesystem_create_directory"
    assert "create_directory" in decision.metadata["requested_actions"]


def test_operational_android_project_and_apk_routes_to_task_preview() -> None:
    decision = ChatOperationRouterService().route(
        r"Crie um jogo Android Kotlin simples em C:\Users\rafae\Documents\TestesIALocal\JogoNovo e gere um APK.",
    )

    assert decision.operation_type == "android_apk_build"
    assert decision.message_type == "task_preview"
    assert {"create_project", "write_files", "run_build", "create_artifact"}.issubset(set(decision.metadata["requested_actions"]))


def test_create_file_maps_to_filesystem_write_file_without_apply_patch_scope() -> None:
    decision = ChatOperationRouterService().route(
        r"Crie um arquivo em C:\Dev\AIpinho\sandboxes\dopamine_test\resultado.txt com o texto: AIpinho funcionou.",
    )

    assert decision.operation_type == "filesystem_write_file"
    assert decision.message_type == "task_status_update"
    assert decision.metadata["approval_scope"] == "filesystem_write"
    assert "apply_patch" not in decision.metadata.get("requested_actions", [])


def test_create_project_maps_to_project_create() -> None:
    decision = ChatOperationRouterService().route(
        r"Crie um projeto simples em C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo.",
    )

    assert decision.operation_type == "project_generation"
    assert decision.metadata["router_operation_type"] == "project_create"
    assert decision.message_type == "task_preview"
    assert decision.metadata["approval_scope"] == "project_write"


def test_public_fact_query_requires_web_or_structured_capability_missing() -> None:
    decision = ChatOperationRouterService().route("Quais foram os ultimos governadores do RJ?")

    assert decision.operation_type == "public_fact_query"
    assert decision.message_type == "assistant_degraded_answer"
    assert decision.metadata["requires_web_search"] is True
    assert decision.metadata["private_rag_required"] is False


def test_explicit_recent_web_search_routes_before_generic_conversation() -> None:
    decision = ChatOperationRouterService().route("Pesquise na internet noticias recentes sobre Android Studio.")

    assert decision.operation_type == "public_fact_query"


def test_deferred_game_idea_remains_conversation_not_project_generation() -> None:
    decision = ChatOperationRouterService().route("Me dê uma ideia simples de jogo mobile para eu criar depois.")

    assert decision.operation_type == "conversation"
    assert decision.metadata["router_operation_type"] == "simple_conversation"
    assert decision.message_type == "assistant_final_answer"
    assert decision.metadata["conversation_kind"] == "brainstorming"


def test_local_file_read_routes_before_public_fact_query() -> None:
    decision = ChatOperationRouterService().route(
        r"Leia o arquivo C:\Dev\AIpinho\sandboxes\dopamine_test\resultado.txt e confirme o conteúdo.",
    )

    assert decision.operation_type == "filesystem_read_file"
    assert decision.metadata["workspace_write"] is False


def test_contextual_append_uses_recent_file_context_contract() -> None:
    decision = ChatOperationRouterService().route("Adicione uma segunda linha no mesmo arquivo: Segunda linha adicionada.")

    assert decision.operation_type == "filesystem_append_file"
    assert decision.metadata["requires_context_path"] is True


def test_destructive_and_git_write_requests_are_policy_blocks() -> None:
    destructive = ChatOperationRouterService().route(r"Apague recursivamente C:\Dev\AIpinho.")
    git_write = ChatOperationRouterService().route("Faça git push automaticamente.")

    assert destructive.operation_type == "dangerous_operation_blocked"
    assert git_write.operation_type == "dangerous_operation_blocked"


def test_sandbox_capability_probe_routes_to_capability_test() -> None:
    decision = ChatOperationRouterService().route("Você consegue escrever arquivos na sandbox agora? Teste criando um arquivo pequeno.")

    assert decision.operation_type == "sandbox_capability_test"


def test_required_attachment_missing_routes_to_structured_block() -> None:
    decision = ChatOperationRouterService().route("Analise com anexo obrigatório e gere um resumo.")

    assert decision.operation_type == "attachment_required_missing"


def test_workspace_summary_and_zip_routes_to_governed_evidence_bundle() -> None:
    decision = ChatOperationRouterService().route(
        """
        No workspace C:\\Example\\Mutable, gere um pacote final de evidencias.
        Crie:
        reports\\closure_summary.md
        reports\\closure_bundle.zip
        O ZIP deve incluir:
        reports\\analysis.md
        README.md
        src\\main\\App.kt
        qualquer relatorio closure presente em reports
        """
    )

    assert decision.operation_type == "workspace_evidence_bundle"
    assert decision.metadata["router_operation_type"] == "workspace_evidence_bundle"
    assert decision.metadata["summary_relative_path"] == "reports/closure_summary.md"
    assert decision.metadata["archive_relative_path"] == "reports/closure_bundle.zip"
    assert "README.md" in decision.metadata["source_relative_paths"]
    assert decision.metadata["include_globs"] == ["reports/*closure*"]


def test_visual_render_qa_routes_to_static_reachability_report() -> None:
    decision = ChatOperationRouterService().route(
        """
        No workspace C:\\Example\\Mutable, valide QA visual.
        Texto esperado:
        Texto humano de status
        Gere:
        reports\\visual_qa.md
        """,
        workspace_hint="C:\\Example\\Mutable",
    )

    assert decision.operation_type == "workspace_static_reachability_report"
    assert decision.metadata["router_operation_type"] == "workspace_static_reachability_report"
    assert decision.metadata["expected_text"] == "Texto humano de status"
    assert decision.metadata["report_relative_path"] == "reports/visual_qa.md"
