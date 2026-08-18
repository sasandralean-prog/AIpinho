from pathlib import Path

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore


def _service(tmp_path: Path) -> CanonicalPublicChatService:
    return CanonicalPublicChatService()


def test_workspace_analysis_report_is_readonly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ChatService, "respond", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy chat must not own readonly analysis")))
    response = _service(tmp_path).respond(
        ChatRequest(
            message=r"Analise os arquivos em C:\Users\rafae\Documents\AIpinhoTestes e crie um plano.",
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.operation_type == "workspace_analysis_readonly"
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert "write_files" not in response.actions


def test_readonly_report_no_project_generation_pending_approval(tmp_path: Path) -> None:
    response = _service(tmp_path).respond(
        ChatRequest(message="Responda com relatorio do que mudar. Nao escreva arquivos.", context=ChatContext(surface="api")),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type in {"product_planning_readonly", "workspace_analysis_readonly"}
    assert response.status != "pending_approval"
    assert response.approval_id is None


def test_firetest_readonly_with_future_workspace_uses_source_path_and_no_approval(tmp_path: Path) -> None:
    source = tmp_path / "SourceGame"
    target = tmp_path / "FutureGame2"
    source.mkdir()
    (source / "build.gradle").write_text("plugins { id 'com.android.application' }\n", encoding="utf-8")
    (source / "settings.gradle").write_text("pluginManagement {}\n", encoding="utf-8")
    (source / "src").mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                f"TESTE DE FOGO 4. Workload read-only: {source}. "
                f"Workspace alvo futuro: {target}. Comece somente pela FASE A read-only. "
                "Nao escreva arquivos. Nao crie artifact. Nao crie ApprovalRequest. "
                "Nao crie TaskRun operacional. Nao rode shell, build, patch, install, delete ou clean. "
                "Faca diagnostico tecnico read-only, estado atual, architecture map, technical project plan e sprint roadmap."
            ),
            context=ChatContext(surface="mobile"),
        ),
        source_channel="mobile_chat",
    )

    assert response.operation_type == "workspace_analysis_readonly"
    assert response.status in {"ok", "partial", "degraded"}
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert response.actions == []
    assert response.policy["read_only"] is True
    assert response.policy["write_allowed"] is False
    assert response.policy["workspace"] == str(source)
    assert str(target) not in response.policy["workspace"]
    assert "WORKSPACE_ANALYSIS_READONLY_READY" in response.message
    assert "ApprovalRequest: nao criado" in response.message


def test_readonly_project_planning_returns_useful_plan_without_approval(tmp_path: Path) -> None:
    source = tmp_path / "SourceApp"
    target = tmp_path / "TargetApp2"
    source.mkdir()
    (source / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n', encoding="utf-8")
    (source / "src").mkdir()
    (source / "src" / "main.js").write_text("console.log('ok')\n", encoding="utf-8")

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                f"TESTE DE FOGO 4 - FASE B: Planejamento governado. "
                f"A Fase A analisou o projeto fonte em \"{source}\". "
                f"O alvo futuro e \"{target}\". "
                "Gere somente um plano governado/preview textual para reconstruir o app no alvo, "
                "com arquivos provaveis, validacoes, riscos e rollback. "
                "Nao escreva arquivos, nao aplique patch, nao rode shell/build, nao crie artifacts "
                "e nao crie approval sem plano executavel completo."
            ),
            context=ChatContext(surface="mobile"),
        ),
        source_channel="mobile_chat",
    )

    assert response.operation_type == "product_planning_readonly"
    assert response.status == "ok"
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert response.actions == []
    assert response.policy["read_only"] is True
    assert response.policy["write_allowed"] is False
    assert response.policy["workspace"] == str(source)
    assert response.policy["target_workspace"] == str(target)
    assert "READONLY_PROJECT_PLAN_READY" in response.message
    assert "Arquivos e areas provaveis" in response.message
    assert "Rollback futuro" in response.message
    assert "TaskPreview real" in response.message


def test_readonly_technical_plan_terms_do_not_return_placeholder(tmp_path: Path) -> None:
    source = tmp_path / "SourceGame"
    target = tmp_path / "TargetGame2"
    source.mkdir()
    (source / "settings.gradle.kts").write_text('pluginManagement { repositories { google() } }\n', encoding="utf-8")
    (source / "build.gradle.kts").write_text("plugins { id(\"com.android.application\") version \"8.0.0\" apply false }\n", encoding="utf-8")
    (source / "app").mkdir()
    (source / "app" / "src").mkdir(parents=True, exist_ok=True)

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Complemento da Fase A: gere um plano tecnico mais profundo, somente read-only. "
                f"Fonte: \"{source}\". Alvo futuro: \"{target}\". "
                "Nao criar arquivo/artifact, nao executar shell/build/test, nao criar TaskPreview/ApprovalRequest "
                "e sem criar preview ainda. Foque em app/src, game loop, componentes, estado atual, estado desejado, "
                "criterios de validacao e proximo passo."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.operation_type == "product_planning_readonly"
    assert response.status == "ok"
    assert response.approval_id is None
    assert response.task_draft_id is None
    assert response.actions == []
    assert response.policy["read_only"] is True
    assert response.policy["write_allowed"] is False
    assert response.policy["workspace"] == str(source)
    assert response.policy["target_workspace"] == str(target)
    assert "READONLY_PROJECT_PLAN_READY" in response.message
    assert "Plano governado read-only gerado" in response.message
    assert "Classifiquei este pedido" not in response.message


def test_controlled_preview_request_creates_pending_approval_with_target_workspace(tmp_path: Path) -> None:
    source = tmp_path / "SourceApp"
    target = tmp_path / "TargetApp2"
    source.mkdir()
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                f"FASE C: crie agora um TaskPreview executavel e um ApprovalRequest para a futura reconstrucao "
                f"do app no alvo \"{target}\" usando a fonte somente leitura \"{source}\". "
                "Nao execute escrita ainda, nao rode shell/build e nao aplique patch agora. "
                "O preview deve conter target_paths reais, project_generation_plan, expected_outputs, "
                "validation_plan e rollback_plan."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "project_generation"
    assert response.approval_id is not None
    assert response.preview_id is not None
    assert response.task_draft_id is not None
    assert response.actions == ["write_files"]
    assert response.policy["permission"] == "ask"
    assert response.policy["approval_created"] is True
    assert str(target) in response.contract_preview["target_paths"]
    assert str(source) not in response.contract_preview["target_paths"]
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    project_plan = draft.intent_map["project_generation_plan"]
    planned_files = project_plan["files_to_create"]
    assert planned_files
    assert all(item.get("content") for item in planned_files)


def test_controlled_preview_with_conditional_no_approval_guard_still_creates_approval(tmp_path: Path) -> None:
    source = tmp_path / "SourceApp"
    target = tmp_path / "TargetApp2"
    source.mkdir()
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "FASE B: crie agora um TaskPreview executavel e um ApprovalRequest para implementar no alvo "
                f"\"{target}\" usando a fonte read-only \"{source}\". "
                "Nao execute escrita ainda, nao rode shell/build/test e nao aplique patch agora. "
                "O preview deve conter target_paths reais, project_generation_plan, expected_outputs, "
                "validation_plan e rollback_plan. "
                "Se nao conseguir criar plano executavel, nao crie ApprovalRequest e explique a causa."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "project_generation"
    assert response.approval_id is not None
    assert response.preview_id is not None
    assert response.task_draft_id is not None
    assert response.actions == ["write_files"]
    assert response.policy["permission"] == "ask"
    assert response.policy["approval_created"] is True
    assert response.governance_lifecycle["intent"]["evidence"] == ["controlled_preview_approval_request_precedence"]


def test_android_mobile_game_preview_uses_real_template_files(tmp_path: Path) -> None:
    source = tmp_path / "LegacyGame"
    target = tmp_path / "GeneratedGame2"
    source.mkdir()
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "FASE B: crie agora um TaskPreview executavel e um ApprovalRequest para implementar "
                f"um jogo mobile Android/Kotlin no alvo \"{target}\" usando a fonte read-only \"{source}\". "
                "Nao execute escrita ainda, nao rode shell/build/test e nao aplique patch agora. "
                "O preview deve conter arquivos reais do projeto, expected_outputs, validation_plan e rollback_plan."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "project_generation"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    planned_files = draft.intent_map["project_generation_plan"]["files_to_create"]
    planned_relative_paths = {item["relative_path"] for item in planned_files}
    assert "settings.gradle.kts" in planned_relative_paths
    assert "app/src/main/AndroidManifest.xml" in planned_relative_paths
    assert any(path.endswith("/GameView.kt") for path in planned_relative_paths)
    assert all(str(item.get("target_path") or "").startswith(str(target)) for item in planned_files)
    assert all(item.get("content") for item in planned_files)
    app_gradle = next(item for item in planned_files if item["relative_path"] == "app/build.gradle.kts")
    assert "compileOptions" in app_gradle["content"]
    assert "JavaVersion.VERSION_17" in app_gradle["content"]
    assert "kotlinOptions" in app_gradle["content"]
    assert 'jvmTarget = "17"' in app_gradle["content"]


def test_controlled_shell_preview_routes_to_run_command_with_shell_plan(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                f"Crie agora um TaskPreview executavel e um ApprovalRequest para executar \"gradle assembleDebug\" "
                f"em \"{target}\". Nao execute antes do approval. "
                "O preview deve conter comando, cwd, expected_outputs, validation_plan e rollback_plan."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "run_command"
    assert response.approval_id is not None
    assert response.actions == ["run_command"]
    assert response.policy["permission"] == "ask"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    assert draft.intent_map["shell_plan"]["command"] == "gradle assembleDebug"
    assert draft.intent_map["shell_plan"]["cwd"] == str(target)
    assert draft.intent_map["shell_plan"]["shell_category"] == "build_shell"


def test_controlled_readonly_shell_diagnostic_preview_uses_readonly_shell_category(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                f"Crie um TaskPreview executavel e ApprovalRequest para executar \"where gradle\" "
                f"em \"{target}\". Nao execute antes do approval. "
                "O preview deve conter comando, cwd, expected_outputs, validation_plan e rollback_plan."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "run_command"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    assert draft.intent_map["shell_plan"]["command"] == "where gradle"
    assert draft.intent_map["shell_plan"]["shell_category"] == "readonly_shell"


def test_shell_recovery_context_does_not_append_narrative_project_phrase_to_target_path(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    target.mkdir()

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "FASE E: recuperacao governada do build. "
                f"O projeto mobile ja foi criado em \"{target}\". "
                "A tentativa governada de build com comando \"gradle assembleDebug\" falhou; "
                "crie o proximo TaskPreview executavel com ApprovalRequest para recuperar o build. "
                "Nao execute antes do approval."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "preview"
    assert response.operation_type == "run_command"
    assert response.approval_id is None
    assert response.contract_preview["target_paths"] == [str(target)]
    assert all("mobile ja foi criado" not in path for path in response.contract_preview["target_paths"])
    assert response.contract_preview["executable_plan_ref"] is None


def test_labeled_shell_command_preserves_nested_quotes(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    target.mkdir()
    gradle = tmp_path / "Tools" / "Gradle" / "bin" / "gradle.bat"
    gradle.parent.mkdir(parents=True)
    gradle.write_text("@echo off\n", encoding="utf-8")

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Crie um TaskPreview executavel com ApprovalRequest.\n"
                "Comando governado:\n"
                f"\"cmd /c \"\"{gradle}\"\" assembleDebug\"\n"
                f"Use cwd/workspace: \"{target}\".\n"
                "Nao execute antes do approval."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "run_command"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    assert draft.intent_map["shell_plan"]["command"] == f'cmd /c "{gradle}" assembleDebug'
    assert draft.intent_map["shell_plan"]["cwd"] == str(target)


def test_labeled_absolute_executable_shell_command_is_accepted(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    target.mkdir()
    gradle = tmp_path / "Tools" / "Gradle" / "bin" / "gradle.bat"
    gradle.parent.mkdir(parents=True)
    gradle.write_text("@echo off\n", encoding="utf-8")

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Crie um TaskPreview executavel com ApprovalRequest.\n"
                "Comando governado:\n"
                f"\"{gradle} assembleDebug\"\n"
                f"Use cwd/workspace: \"{target}\".\n"
                "Nao execute antes do approval."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "run_command"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    assert draft.intent_map["shell_plan"]["command"] == f"{gradle} assembleDebug"
    assert draft.intent_map["shell_plan"]["shell_category"] == "build_shell"


def test_android_sdk_location_failure_generates_local_properties_plan(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    sdk = tmp_path / "Android" / "Sdk"
    target.mkdir()
    sdk.mkdir(parents=True)

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Build falhou porque SDK location not found. "
                "Gradle informou configurar sdk.dir em local.properties. "
                f"Android SDK local conhecido: \"{sdk}\". "
                f"Workspace alvo: \"{target}\". "
                "Crie um TaskPreview executavel com ApprovalRequest para aplicar a menor correcao "
                "governada no workspace alvo. Esta fase deve ser write/config, nao shell/build."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "project_generation"
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    files = draft.intent_map["project_generation_plan"]["files_to_create"]
    assert [item["relative_path"] for item in files] == ["local.properties"]
    assert f"sdk.dir={str(sdk).replace(chr(92), '/')}" in files[0]["content"]


def test_android_jvm_target_mismatch_generates_gradle_alignment_plan(tmp_path: Path) -> None:
    target = tmp_path / "GeneratedGame2"
    app = target / "app"
    app.mkdir(parents=True)
    (app / "build.gradle.kts").write_text(
        'plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }\n\n'
        'android {\n'
        '    namespace = "br.com.example.game"\n'
        '    compileSdk = 35\n'
        '    defaultConfig { applicationId = "br.com.example.game"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "1.0" }\n'
        '}\n',
        encoding="utf-8",
    )

    response = _service(tmp_path).respond(
        ChatRequest(
            message=(
                "Build Android/Kotlin falhou com erro generico de Gradle: "
                "Execution failed for task ':app:compileDebugKotlin'. "
                "Inconsistent JVM-target compatibility detected for tasks "
                "'compileDebugJavaWithJavac' (1.8) and 'compileDebugKotlin' (17). "
                f"Workspace alvo: \"{target}\". "
                "Crie um TaskPreview executavel com ApprovalRequest para corrigir a configuracao "
                "de JVM target no projeto Android. Nao execute escrita sem approval."
            ),
            context=ChatContext(surface="mobile", active_workspace=str(target)),
        ),
        source_channel="mobile_chat",
    )

    assert response.status == "pending_approval"
    assert response.operation_type == "project_generation"
    assert response.approval_id is not None
    draft = TaskDraftStore().get(str(response.task_draft_id))
    assert draft is not None
    plan = draft.intent_map["project_generation_plan"]
    assert plan["analysis_summary"]["reason_code"] == "android_kotlin_java_jvm_target_mismatch"
    files = plan["files_to_modify"]
    assert [item["relative_path"] for item in files] == ["app/build.gradle.kts"]
    assert "compileOptions" in files[0]["content"]
    assert "JavaVersion.VERSION_17" in files[0]["content"]
    assert "kotlinOptions" in files[0]["content"]
    assert 'jvmTarget = "17"' in files[0]["content"]
