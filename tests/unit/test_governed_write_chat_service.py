from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.governed_write_chat_service import GovernedWriteChatService
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner


class FakeShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


def _config_root(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True)
    for filename in ["tool_gateway_registry.yaml", "tool_gateway_policy.yaml"]:
        (config_root / "agents" / filename).write_text(Path("config/agents", filename).read_text(encoding="utf-8"), encoding="utf-8")
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: source
    root: {source}
    role: source_readonly
    enabled: true
  - workspace_id: target
    root: {target}
    role: target_mutable
    enabled: true
""",
        encoding="utf-8",
    )
    return config_root, source, target


def _chat_service(tmp_path: Path) -> tuple[ChatService, Path, Path]:
    config_root, source, target = _config_root(tmp_path)
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    governed_write = GovernedWriteChatService(kernel=kernel, tool_gateway=gateway, require_chat_write_approval=False)
    return ChatService(governed_write_service=governed_write), source, target


def test_chat_governed_file_write_creates_file_in_target_workspace(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message="Crie no workspace alvo um arquivo README_TESTE.md com conteudo 'teste de escrita governada'.",
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status == "ok"
    assert response.operation_type == "governed_file_write"
    assert response.task_id
    assert response.evidence_refs
    assert (target / "README_TESTE.md").read_text(encoding="utf-8") == "teste de escrita governada\n"


def test_chat_governed_file_write_creates_nested_relative_file_in_target_workspace(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message=(
                "Crie o arquivo reports/health.md dentro do workspace alvo com titulo, "
                "timestamp, lista de arquivos detectados e status READY."
            ),
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    report = target / "reports" / "health.md"
    assert response.status == "ok"
    assert response.operation_type == "governed_file_write"
    assert response.task_id
    assert report.exists()
    assert report.stat().st_size > 0
    content = report.read_text(encoding="utf-8")
    assert "Data\n" in content
    assert "Workspace\n" in content
    assert "Status\nREADY" in content


def test_chat_governed_file_write_resolves_absolute_registered_workspace_path(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message=(
                f"Crie o arquivo reports/health.md dentro do workspace alvo {target} "
                "com titulo, timestamp, lista de arquivos detectados e status READY."
            ),
            context=ChatContext(surface="api"),
        )
    )

    report = target / "reports" / "health.md"
    assert response.status == "ok"
    assert response.policy["workspace_id"] == "target"
    assert report.exists()
    assert report.stat().st_size > 0


def test_chat_governed_file_write_respects_resolved_child_workspace_path(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)
    child_workspace = target / "child_project"
    child_workspace.mkdir()

    response = service.respond(
        ChatRequest(
            message=(
                f"Crie o arquivo reports/health.md dentro do workspace alvo {child_workspace} "
                "com titulo, timestamp, lista de arquivos detectados e status READY."
            ),
            context=ChatContext(surface="api"),
        )
    )

    child_report = child_workspace / "reports" / "health.md"
    parent_report = target / "reports" / "health.md"
    assert response.status == "ok"
    assert response.policy["workspace_id"] == "target"
    assert child_report.exists()
    assert child_report.stat().st_size > 0
    assert not parent_report.exists()


def test_chat_governed_file_write_modifies_existing_file_in_target_workspace(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)
    existing = target / "README_EXISTENTE.md"
    existing.write_text("# Existente\n", encoding="utf-8")

    response = service.respond(
        ChatRequest(
            message="Modifique o arquivo README_EXISTENTE.md no workspace alvo adicionando a secao Validacao com uma frase curta.",
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status == "ok"
    assert response.operation_type == "governed_file_write"
    assert response.task_id
    content = existing.read_text(encoding="utf-8")
    assert "# Existente" in content
    assert "## Validacao" in content


def test_chat_governed_ui_text_update_infers_source_file(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)
    ui_file = target / "src" / "main" / "kotlin" / "example" / "ui" / "AppScreen.kt"
    ui_file.parent.mkdir(parents=True)
    ui_file.write_text(
        """package example.ui

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.foundation.layout.Column

@Composable
fun AppScreen() {
    Column {
        Text("Bem-vindo")
    }
}
""",
        encoding="utf-8",
    )

    response = service.respond(
        ChatRequest(
            message='Implemente uma pequena melhoria de UX: adicione o texto visivel "Sistema pronto" na tela principal do app. Valide que o texto aparece em algum arquivo fonte.',
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status == "ok"
    assert response.operation_type == "governed_file_write"
    assert response.policy["validation_status"] == "passed"
    content = ui_file.read_text(encoding="utf-8")
    assert "Sistema pronto" in content
    assert 'Text("Sistema pronto"' in content


def test_chat_governed_file_write_blocks_source_readonly(tmp_path: Path) -> None:
    service, source, _ = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message="Crie no workspace alvo um arquivo BLOQUEADO.md com conteudo 'nao deve gravar'.",
            context=ChatContext(surface="api", active_workspace="source"),
        )
    )

    assert response.status == "blocked"
    assert response.policy["reason_code"] == "source_readonly_write_denied"
    assert not (source / "BLOQUEADO.md").exists()


def test_chat_governed_file_write_without_workspace_requests_clarification(tmp_path: Path) -> None:
    service, _, _ = _chat_service(tmp_path)

    response = service.respond(ChatRequest(message="Crie um arquivo README_TESTE.md com conteudo 'x'."))

    assert response.status == "needs_clarification"
    assert response.message_type == "clarification_request"
    assert "workspace" in response.message.casefold()


def test_registered_target_mutable_workspace_write_requires_approval_by_default(tmp_path: Path) -> None:
    config_root, _source, target = _config_root(tmp_path)
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel_default_guard"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway_default_guard"),
        shell_runner=FakeShellRunner(),
    )
    service = ChatService(governed_write_service=GovernedWriteChatService(kernel=kernel, tool_gateway=gateway, require_chat_write_approval=True))

    response = service.respond(
        ChatRequest(
            message="Crie no workspace alvo um arquivo README_TESTE.md com conteudo 'teste de escrita governada'.",
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status == "pending_approval"
    assert response.requires_user_action is True
    assert response.policy["approval_required_for"] == ["create_file"]
    assert not (target / "README_TESTE.md").exists()


def test_negative_constraints_block_governed_write_even_when_filename_is_present(tmp_path: Path) -> None:
    service, _, target = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message=(
                "Leia apenas metadados do workspace. Nao crie arquivo. Nao gere relatorio. "
                "Responda somente no chat: 1. existe build.gradle?"
            ),
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status in {"ok", "blocked", "degraded"}
    assert response.policy.get("workspace_write") is False
    assert not (target / "1. existe build.gradle").exists()


def test_chat_readonly_analysis_with_active_workspace_does_not_become_patch_request(tmp_path: Path) -> None:
    service, source, _ = _chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message="Analise o source project em modo somente leitura. Gere um relatorio markdown com riscos. Nao altere arquivos.",
            context=ChatContext(surface="api", active_workspace="source"),
        )
    )

    assert response.status == "preview"
    assert response.operation_type == "readonly_project_analysis"
    assert response.policy["read_only"] is True
    assert response.grounding_missing_reason == "read_files_not_executed"
    assert list(source.iterdir()) == []


def test_governed_write_resolves_registered_workspace_id_before_relative_path() -> None:
    class FakeWorkspaceResolver:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def resolve(self, *, workspace_id=None, path_ref=None, access="read"):
            if workspace_id is not None:
                self.calls.append(("workspace_id", workspace_id))
                return SimpleNamespace(workspace_id=workspace_id, reason_code=None, allowed=True)
            self.calls.append(("path_ref", path_ref))
            return SimpleNamespace(workspace_id="wrong_relative_path", reason_code=None, allowed=True)

    resolver = FakeWorkspaceResolver()
    service = GovernedWriteChatService(workspace_resolver=resolver)

    workspace = service._resolve_workspace("target")

    assert workspace.workspace_id == "target"
    assert resolver.calls == [("workspace_id", "target")]


def test_filename_extraction_accepts_safe_relative_path_and_rejects_escape_paths() -> None:
    planner = AgentLocalActionPlanner()

    assert planner.extract_requested_filename("Crie o arquivo reports\\health.md dentro do workspace alvo.") == "reports/health.md"
    assert planner.extract_requested_filename("Gere um relatorio em:\n\nreports/project_scan.md") == "reports/project_scan.md"
    assert planner.extract_requested_filename("Gere relatorio em reports/persistence_fix.md") == "reports/persistence_fix.md"
    assert planner.extract_requested_filename("Atualize o README.md sem remover conteudo existente.") == "README.md"
    assert planner.extract_requested_filename("Responda somente no chat:\n1. existe build.gradle?\n2. existe package.json?") is None
    assert planner.extract_requested_section('Adicione uma secao chamada "Firetest AIpinho". A secao deve resumir que o fluxo e governado.') == "Firetest AIpinho"
    assert "fluxo e governado" in (planner.extract_requested_section_body('Adicione uma secao chamada "Firetest AIpinho". A secao deve resumir que o fluxo e governado.') or "")
    assert planner._safe_relative_filename("docs/report.txt") == "docs/report.txt"
    assert planner._safe_relative_filename(r"C:\Windows\System32\evil.txt") is None
    assert planner._safe_relative_filename("../evil.txt") is None


def test_requested_file_content_uses_directed_source_diagnosis_for_persistence(tmp_path: Path) -> None:
    source = tmp_path / "source"
    code_dir = source / "src" / "data"
    code_dir.mkdir(parents=True)
    (code_dir / "Repository.kt").write_text(
        """
class Repository(private val dataFile: Path) {
    fun loadWithResult(): LoadResult {
        if (!dataFile.exists()) return LoadResult(demoData(), loadedFromDisk = false)
        val text = Files.readString(dataFile)
        return LoadResult(decode(text), loadedFromDisk = true)
    }

    fun save(data: Data) {
        Files.writeString(dataFile, encode(data))
    }

    fun exportJson(data: Data): Path {
        val path = dataFile.resolveSibling("export.json")
        Files.writeString(path, encode(data))
        return path
    }

    fun demoData(): Data = Data()
}
""",
        encoding="utf-8",
    )

    content = AgentLocalActionPlanner().content_for_requested_file(
        "Investigue a persistencia do projeto. Gere relatorio em reports/persistence.md. "
        "Inclua arquivo responsavel, funcao de load, funcao de save/export, evidencia textual e veredito.",
        workspace_context=str(source),
    )

    assert "Diagnostico dirigido de persistencia" in content
    assert "src/data/Repository.kt" in content
    assert "loadWithResult" in content
    assert "save" in content
    assert "exportJson" in content
    assert "persistence_real" in content
    assert "Evidencia textual" in content


def test_requested_file_content_answers_explicit_workspace_checklist(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "package.json").write_text(
        json.dumps(
            {
                "scripts": {"android": "react-native run-android", "build": "gradle assembleDebug"},
                "dependencies": {"react": "latest", "react-native": "latest"},
                "devDependencies": {},
            }
        ),
        encoding="utf-8",
    )
    (source / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (source / "index.js").write_text("console.log('app')\n", encoding="utf-8")

    prompt = """
    Faca um preflight read-only do projeto.

    Erro observado:
    Unable to load script. Make sure your bundle 'index.android.bundle' is packaged correctly.

    Gere relatorio em reports/preflight.md

    O relatorio deve conter:
    * stack detectada;
    * package manager detectado;
    * presenca/ausencia de android/;
    * presenca/ausencia de package.json;
    * presenca/ausencia de index.js/index.ts;
    * presenca/ausencia de android/app/src/main/assets/index.android.bundle;
    * comandos de build provaveis;
    * causa provavel;
    * riscos;
    * proxima acao recomendada.
    """

    content = AgentLocalActionPlanner().content_for_requested_file(prompt, workspace_context=str(source))

    assert "Checklist solicitado" in content
    assert "Runtime React Native/Expo detectado" in content
    assert "package manager detectado: pnpm" in content
    assert "android/: ausente" in content
    assert "package.json: presente" in content
    assert "index.js/index.ts: presente" in content
    assert "android/app/src/main/assets/index.android.bundle: ausente" in content
    assert "android: `react-native run-android`" in content
    assert "bundle JS Android ausente" in content or "diretorio android" in content


def test_runtime_load_script_diagnosis_does_not_use_persistence_template(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "package.json").write_text(
        json.dumps({"scripts": {"build": "pnpm build"}, "dependencies": {"react-native": "latest"}}),
        encoding="utf-8",
    )
    prompt = """
    Diagnostique por que o APK mostra Unable to load script.

    Gere relatorio em reports/runtime.md

    Inclua:
    * se depende de Metro;
    * se o bundle JS esta ausente;
    * se ha comando para gerar APK offline;
    * veredito: bundle_missing, metro_required, build_misconfigured, project_incomplete, dependency_missing ou unknown.
    """

    content = AgentLocalActionPlanner().content_for_requested_file(prompt, workspace_context=str(source))

    assert "Diagnostico dirigido de persistencia" not in content
    assert "Checklist solicitado" in content
    assert "bundle JS" in content


def test_runtime_correction_plan_checklist_gets_structural_answers(tmp_path: Path) -> None:
    source = tmp_path / "source"
    mobile = source / "artifacts" / "mobile"
    mobile.mkdir(parents=True)
    (source / "package.json").write_text(
        json.dumps({"scripts": {"build": "pnpm -r --if-present run build"}, "dependencies": {"expo": "latest", "react-native": "latest"}}),
        encoding="utf-8",
    )
    (mobile / "package.json").write_text(
        json.dumps({"scripts": {"build": "node scripts/build.js", "typecheck": "tsc -p tsconfig.json --noEmit"}}),
        encoding="utf-8",
    )
    (mobile / "eas.json").write_text(json.dumps({"build": {"preview": {"android": {"buildType": "apk"}}}}), encoding="utf-8")
    (mobile / "scripts").mkdir()
    (mobile / "scripts" / "build.js").write_text("console.log('build')", encoding="utf-8")

    prompt = """
    Prepare um plano de correcao minimo para fazer o APK abrir sem o erro 'Unable to load script'.

    O plano deve conter:
    - problema raiz confirmado ou mais provavel;
    - estrategia minima;
    - arquivos candidatos;
    - comandos candidatos;
    - validation plan;
    - rollback plan;
    - approval_required true/false;
    - criterio de sucesso;
    - proximo passo recomendado.
    """

    content = AgentLocalActionPlanner().content_for_requested_file(prompt, workspace_context=str(source))

    assert "Item registrado para revisao" not in content
    assert "bundle" in content
    assert "artifacts/mobile/package.json" in content
    assert "artifacts/mobile/scripts/build.js" in content
    assert "validacao governada" in content
    assert "true para qualquer patch" in content
    assert "APK debug/offline" in content
