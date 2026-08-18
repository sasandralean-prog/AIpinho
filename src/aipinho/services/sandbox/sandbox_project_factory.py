from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest, AgentRunUpdateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.project_generation import (
    ProjectGenerationRequest,
    ProjectGenerationResult,
    ProjectGenerationRouteDecision,
    ProjectType,
)
from aipinho.schemas.sandbox import SandboxValidationResult
from aipinho.schemas.templates import TemplateExecutionRequest, TemplateExecutionResult
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.sandbox.project_templates import (
    android_kotlin_simple_game_template,
    generic_files_template,
    python_simple_app_template,
    static_web_template,
)
from aipinho.services.sandbox.project_templates.project_manifest import project_manifest_json
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.services.templates.template_execution_service import TemplateExecutionService
from aipinho.services.templates.template_registry_service import TemplateRegistryService


class SandboxProjectFactory:
    WINDOWS_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|`[a-z]:\\|\"[a-z]:\\)")

    def __init__(
        self,
        *,
        workspaces: SandboxWorkspaceService | None = None,
        gateway: AgentToolGatewayService | None = None,
        kernel: AgentSessionKernelService | None = None,
        store: SandboxStoreService | None = None,
        template_registry: TemplateRegistryService | None = None,
        template_executor: TemplateExecutionService | None = None,
    ) -> None:
        self.store = store or SandboxStoreService()
        self.workspaces = workspaces or SandboxWorkspaceService(store=self.store)
        self.kernel = kernel or AgentSessionKernelService()
        self.gateway = gateway or AgentToolGatewayService(kernel=self.kernel)
        self.template_registry = template_registry or TemplateRegistryService()
        self.template_executor = template_executor or TemplateExecutionService(registry=self.template_registry)
        self._last_template_execution: TemplateExecutionResult | None = None

    def classify_goal(self, user_goal: str) -> ProjectGenerationRouteDecision:
        goal = user_goal.casefold()
        has_external_path = bool(self.WINDOWS_PATH_RE.search(user_goal))
        asks_create = any(token in goal for token in ("crie", "criar", "gere", "gerar", "generate", "create"))
        asks_project = any(token in goal for token in ("projeto", "app", "demo", "landing", "cli", "jogo", "game"))
        asks_zip = ".zip" in goal or " zip" in goal or "compact" in goal
        project_type = self.infer_project_type(user_goal)

        if has_external_path and not asks_create:
            return ProjectGenerationRouteDecision(
                status="blocked",
                route_type="external_path_requires_workspace",
                project_type=project_type,
                requires_workspace=True,
                use_sandbox=False,
                safe_alternative="Nao posso ler esse path sem workspace registrado, mas posso criar uma versao nova dentro do sandbox e gerar um zip baixavel.",
                reasons=["external_path_detected", "workspace_required_for_external_read"],
                evidence_refs=["route:external_path_requires_workspace"],
            )
        if asks_create or asks_project or asks_zip:
            return ProjectGenerationRouteDecision(
                status="ok",
                route_type="sandbox_project_generation" if asks_project else "sandbox_artifact_request",
                project_type=project_type,
                project_name=self.infer_project_name(user_goal),
                requires_workspace=False,
                use_sandbox=True,
                reasons=["new_generation_request", "sandbox_allowed_for_new_work"],
                evidence_refs=["route:sandbox_project_generation"],
            )
        return ProjectGenerationRouteDecision(
            status="needs_clarification",
            route_type="clarification_needed",
            project_type=project_type,
            reasons=["generation_intent_not_confident"],
            evidence_refs=["route:clarification_needed"],
        )

    def generate(self, request: ProjectGenerationRequest) -> ProjectGenerationResult:
        started_at = utc_now_iso()
        route = self.classify_goal(request.user_goal)
        if route.requires_workspace and not route.use_sandbox:
            task = self.workspaces.create_task(
                sandbox_workspace_id=request.sandbox_workspace_id,
                title="Blocked external path request",
                created_by_agent_id=request.requesting_agent_id,
            )
            return ProjectGenerationResult(
                project_generation_id=request.project_generation_id,
                sandbox_task_id=task.sandbox_task_id,
                sandbox_workspace_id=request.sandbox_workspace_id,
                status="blocked",
                project_root="",
                project_name=request.project_name or "external_path_request",
                project_type=route.project_type,
                final_answer_sanitized=route.safe_alternative or "A operacao exige workspace registrado.",
                evidence_refs=route.evidence_refs,
                errors=["external_path_requires_workspace"],
                started_at=started_at,
                completed_at=utc_now_iso(),
                metadata_sanitized={"route_decision": route.model_dump()},
            )

        project_type = request.project_type if request.project_type != "unknown" else route.project_type
        project_name = request.project_name or route.project_name or self.infer_project_name(request.user_goal) or "sandbox_project"
        project_slug = self._safe_slug(project_name)
        zip_name = self._safe_filename(request.output_zip_name or f"{project_slug}.zip")
        workspace = self.workspaces.get_workspace(request.sandbox_workspace_id)
        task = self.workspaces.get_task(request.sandbox_task_id) if request.sandbox_task_id else self.workspaces.create_task(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            title=f"Generate {project_name}",
            created_by_agent_id=request.requesting_agent_id,
        )
        session = self.kernel.create_session(
            request.requesting_agent_id,
            AgentSessionCreateRequest(title=f"Sandbox Project Factory - {project_name}"),
        )
        run = self.kernel.create_run(
            request.requesting_agent_id,
            session.session_id,
            AgentRunCreateRequest(
                operation_type="sandbox_project_generation",
                status="running",
                metadata_sanitized={
                    "project_generation_id": request.project_generation_id,
                    "project_type": project_type,
                    "sandbox_task_id": task.sandbox_task_id,
                    "sandbox_workspace_id": workspace.sandbox_workspace_id,
                },
            ),
        )

        self._last_template_execution = None
        files = self._build_template(request, project_name=project_name, project_type=project_type)
        template_execution = self._last_template_execution
        manifest_rel = f"{project_slug}/PROJECT_MANIFEST.json"
        files[manifest_rel] = project_manifest_json(
            project_name=project_name,
            sandbox_task_id=task.sandbox_task_id,
            project_generation_id=request.project_generation_id,
            project_type=project_type,
            files=sorted(files.keys()),
            assets=sorted([path for path in files if "/res/drawable/" in path]),
            features=request.requested_features,
            validation_status="pending",
            artifact_id="assigned_after_export",
            warnings=[],
            evidence_refs=[f"sandbox_task:{task.sandbox_task_id}", f"run:{run.run_id}"],
            metadata_sanitized={
                "template_id": template_execution.template_id if template_execution else None,
                "template_version": template_execution.template_version if template_execution else None,
                "template_execution_id": template_execution.template_execution_id if template_execution else None,
            },
        )

        files_created: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        evidence_refs = [f"sandbox_task:{task.sandbox_task_id}", f"run:{run.run_id}"]
        for relative_path, content in files.items():
            result = self.gateway.invoke(
                request.requesting_agent_id,
                run.run_id,
                "sandbox_write_file",
                ToolInvocationCreateRequest(
                    sandbox_workspace_id=workspace.sandbox_workspace_id,
                    sandbox_task_id=task.sandbox_task_id,
                    relative_path=relative_path,
                    operation_scope="sandbox",
                    operation_type="sandbox_project_file_write",
                    input={
                        "content": content,
                        "overwrite": True,
                    },
                    metadata_sanitized={"project_generation_id": request.project_generation_id},
                ),
            )
            if result.status != "succeeded":
                errors.append(f"write_failed:{relative_path}:{result.status}")
            else:
                files_created.append(relative_path)
                evidence_refs.append(f"tool:{result.tool_invocation.tool_invocation_id}")

        validation = self._structural_validate(
            sandbox_task_id=task.sandbox_task_id,
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            project_root=project_slug,
            project_type=project_type,
            template_id=template_execution.template_id if template_execution else None,
        )
        evidence_refs.extend(validation.evidence_refs)
        validation_ids = [validation.validation_id]
        if validation.status != "passed":
            self.workspaces.update_task_status(task.sandbox_task_id, "failed", evidence_refs=evidence_refs)
            self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status="validation_failed"))
            return ProjectGenerationResult(
                project_generation_id=request.project_generation_id,
                sandbox_task_id=task.sandbox_task_id,
                sandbox_workspace_id=workspace.sandbox_workspace_id,
                status="validation_failed",
                project_root=project_slug,
                project_name=project_name,
                project_type=project_type,
                files_created=files_created,
                assets_created=[path for path in files_created if "/res/drawable/" in path],
                validation_ids=validation_ids,
                final_answer_sanitized="A geracao criou arquivos, mas a validacao estrutural falhou. Nenhum artifact pronto foi declarado.",
                evidence_refs=evidence_refs,
                warnings=warnings,
                errors=[*errors, *validation.errors],
                started_at=started_at,
                completed_at=utc_now_iso(),
                metadata_sanitized={"route_decision": route.model_dump()},
            )

        build_warning = self._try_optional_build_or_syntax(request, run.run_id, workspace.sandbox_workspace_id, task.sandbox_task_id, project_slug, project_type)
        if build_warning:
            warnings.append(build_warning)

        export_result = None
        artifact_ids: list[str] = []
        zip_artifact_id: str | None = None
        download_endpoint: str | None = None
        if request.artifact_requested:
            export_result = self.gateway.invoke(
                request.requesting_agent_id,
                run.run_id,
                "sandbox_zip_export",
                ToolInvocationCreateRequest(
                    sandbox_workspace_id=workspace.sandbox_workspace_id,
                    sandbox_task_id=task.sandbox_task_id,
                    operation_scope="sandbox",
                    operation_type="sandbox_project_zip_export",
                    input={
                        "filename": zip_name,
                        "include_paths": [project_slug],
                        "project_generation_id": request.project_generation_id,
                    },
                    metadata_sanitized={"project_generation_id": request.project_generation_id},
                ),
            )
            if export_result.status == "succeeded" and export_result.artifacts:
                artifact = export_result.artifacts[0]
                zip_artifact_id = artifact.artifact_id
                artifact_ids.append(artifact.artifact_id)
                download_endpoint = artifact.download_endpoint
                evidence_refs.extend([f"artifact:{artifact.artifact_id}", f"tool:{export_result.tool_invocation.tool_invocation_id}"])
            else:
                errors.append(f"artifact_export_failed:{export_result.status}")

        status = "completed_with_warnings" if warnings else "completed"
        if request.artifact_requested and not zip_artifact_id:
            status = "artifact_failed"
        final_answer = self._final_answer(project_name=project_name, zip_name=zip_name, artifact_id=zip_artifact_id, errors=errors, warnings=warnings)
        self.workspaces.update_task_status(
            task.sandbox_task_id,
            "completed" if status in {"completed", "completed_with_warnings"} else "failed",
            evidence_refs=evidence_refs,
            completed=status in {"completed", "completed_with_warnings"},
        )
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status="completed" if status in {"completed", "completed_with_warnings"} else "failed",
                artifact_ids=artifact_ids,
                metadata_sanitized={
                    "project_generation_id": request.project_generation_id,
                    "project_type": project_type,
                    "sandbox_task_id": task.sandbox_task_id,
                    "sandbox_workspace_id": workspace.sandbox_workspace_id,
                    "latest_summary_sanitized": final_answer,
                    "evidence_refs": evidence_refs,
                    "template_id": template_execution.template_id if template_execution else None,
                    "template_version": template_execution.template_version if template_execution else None,
                    "template_execution_id": template_execution.template_execution_id if template_execution else None,
                },
            ),
        )
        return ProjectGenerationResult(
            project_generation_id=request.project_generation_id,
            sandbox_task_id=task.sandbox_task_id,
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            status=status,
            project_root=project_slug,
            project_name=project_name,
            project_type=project_type,
            files_created=files_created,
            assets_created=[path for path in files_created if "/res/drawable/" in path],
            validation_ids=validation_ids,
            artifact_ids=artifact_ids,
            zip_artifact_id=zip_artifact_id,
            download_endpoint=download_endpoint,
            final_answer_sanitized=final_answer,
            evidence_refs=evidence_refs,
            warnings=warnings,
            errors=errors,
            started_at=started_at,
            completed_at=utc_now_iso(),
            metadata_sanitized={
                "route_decision": route.model_dump(),
                "export": export_result.output if export_result else None,
                "template_id": template_execution.template_id if template_execution else None,
                "template_version": template_execution.template_version if template_execution else None,
                "template_execution_id": template_execution.template_execution_id if template_execution else None,
            },
        )

    def infer_project_type(self, user_goal: str) -> ProjectType:
        goal = user_goal.casefold()
        if "android" in goal or "kotlin" in goal:
            if any(token in goal for token in ("jogo", "game", "arcade", "pular", "obstaculo", "obstacle")):
                return "android_kotlin"
            return "android_kotlin_app"
        if "fastapi" in goal or ("python" in goal and any(token in goal for token in ("api", "endpoint", "backend"))):
            return "python_fastapi"
        if "python" in goal and "cli" in goal:
            return "python_cli"
        if "python" in goal:
            return "python_simple_app"
        if any(token in goal for token in ("html", "css", "javascript", "landing page", "web")):
            return "static_web"
        if any(token in goal for token in ("markdown", "documentacao", "documentação", "docs", "runbook")):
            return "docs_pack"
        if any(token in goal for token in ("componente mobile", "mobile component", "componente android")):
            return "mobile_component_demo"
        if any(token in goal for token in ("launcher tool", "ferramenta launcher", "desktop tool")):
            return "launcher_tool_demo"
        return "generic_files"

    def infer_project_name(self, user_goal: str) -> str | None:
        explicit_match = re.search(
            r"(?i)(?:chamado|chamada|nomeado|nomeada|named|called)\s+([A-Za-z][A-Za-z0-9_-]{2,})",
            user_goal,
        )
        if explicit_match:
            return explicit_match.group(1)
        zip_match = re.search(r"([A-Za-z][A-Za-z0-9_-]+)\.zip", user_goal)
        if zip_match:
            return zip_match.group(1)
        project_match = re.search(r"(?i)\bprojeto\s+([A-Za-z][A-Za-z0-9_-]{2,})", user_goal)
        if project_match:
            return project_match.group(1)
        return None

    def _build_template(self, request: ProjectGenerationRequest, *, project_name: str, project_type: ProjectType) -> dict[str, str]:
        project_slug = self._safe_slug(project_name)
        assets = self._asset_names(request)
        manifest = self.template_registry.find(
            project_type=project_type,
            language=request.language,
            platform=request.target_platform,
            user_goal=request.user_goal,
        )
        if manifest is not None:
            bundle = self.template_executor.render(
                TemplateExecutionRequest(
                    template_id=manifest.template_id,
                    template_version=manifest.version,
                    sandbox_task_id=request.sandbox_task_id,
                    session_id=request.session_id,
                    requesting_agent_id=request.requesting_agent_id,
                    user_goal=request.user_goal,
                    project_name=project_name,
                    requested_assets=assets or request.requested_assets,
                    output_zip_name=request.output_zip_name,
                    validation_level=request.validation_level,
                    build_if_available=request.build_if_possible,
                    artifact_requested=request.artifact_requested,
                    metadata_sanitized={
                        **request.metadata_sanitized,
                        "project_type": project_type,
                        "selected_by": "template_registry",
                    },
                )
            )
            if bundle.execution.status == "completed":
                self._last_template_execution = bundle.execution
                return {f"{project_slug}/{path}": content for path, content in bundle.files.items()}

        if project_type == "android_kotlin":
            package_name = f"br.com.aipinho.sandbox.{project_slug.casefold()}"
            files = android_kotlin_simple_game_template(
                project_name=project_name,
                package_name=package_name,
                character_asset=assets[0] if assets else "character",
                obstacle_asset=assets[1] if len(assets) > 1 else "obstacle",
            )
        elif project_type in {"python_cli", "python_simple_app"}:
            files = python_simple_app_template(project_name=project_name)
        elif project_type == "static_web":
            files = static_web_template(project_name=project_name)
        else:
            files = generic_files_template(project_name=project_name, user_goal=request.user_goal)
        return {f"{project_slug}/{path}": content for path, content in files.items()}

    def _asset_names(self, request: ProjectGenerationRequest) -> list[str]:
        names = [Path(item).stem for item in request.requested_assets]
        names.extend(Path(match).stem for match in re.findall(r"([A-Za-z0-9_-]+\.png)", request.user_goal))
        safe: list[str] = []
        for name in names:
            slug = self._safe_slug(name).casefold()
            if slug and slug not in safe:
                safe.append(slug)
        return safe

    def _structural_validate(
        self,
        *,
        sandbox_task_id: str,
        sandbox_workspace_id: str,
        project_root: str,
        project_type: ProjectType,
        template_id: str | None = None,
    ) -> SandboxValidationResult:
        root = self.workspaces.operation_root(sandbox_workspace_id, sandbox_task_id) / project_root
        required = self._required_files(project_type, template_id=template_id)
        checks: list[dict[str, Any]] = []
        errors: list[str] = []
        for rel in required:
            exists = (root / rel).exists()
            checks.append({"type": "file_exists", "relative_path": f"{project_root}/{rel}", "status": "passed" if exists else "failed"})
            if not exists:
                errors.append(f"missing_file:{rel}")
        if template_id == "android_kotlin_game" or (template_id is None and project_type == "android_kotlin"):
            game_files = list(root.glob("app/src/main/java/**/GameView.kt"))
            main_files = list(root.glob("app/src/main/java/**/MainActivity.kt"))
            game_text = game_files[0].read_text(encoding="utf-8", errors="replace") if game_files else ""
            main_text = main_files[0].read_text(encoding="utf-8", errors="replace") if main_files else ""
            content_expectations = {
                "main_references_game_view": "GameView(this)" in main_text,
                "spawn_delay_10_seconds": "spawnDelayMs = 10_000L" in game_text,
                "score_increment": "score += 1" in game_text,
                "collision": "hasCollision" in game_text,
                "reset": "resetGame" in game_text,
                "jumpable_spacing": "minObstacleSpacingPx" in game_text,
                "obstacles": "Obstacle" in game_text,
            }
            for name, passed in content_expectations.items():
                checks.append({"type": "content_check", "name": name, "status": "passed" if passed else "failed"})
                if not passed:
                    errors.append(f"content_check_failed:{name}")
        result = SandboxValidationResult(
            sandbox_task_id=sandbox_task_id,
            validation_type=f"project_structure:{project_type}",
            status="passed" if not errors else "failed",
            checks=checks,
            checked_files=[f"{project_root}/{item}" for item in required],
            errors=errors,
            evidence_refs=[f"sandbox_validation:project_structure", f"sandbox_task:{sandbox_task_id}"],
        )
        self.store.append_trace(sandbox_task_id, {"type": "sandbox_project_validation_finished", "validation_id": result.validation_id, "status": result.status, "project_type": project_type})
        task = self.store.get_task(sandbox_task_id)
        if task is not None:
            self.store.save_task(task.model_copy(update={"validation_ids": [*task.validation_ids, result.validation_id]}))
        return result

    def _required_files(self, project_type: ProjectType, *, template_id: str | None = None) -> list[str]:
        if template_id:
            manifest = self.template_registry.get(template_id)
            if manifest is not None and manifest.required_files:
                return manifest.required_files
        if project_type == "android_kotlin":
            return [
                "settings.gradle.kts",
                "build.gradle.kts",
                "app/build.gradle.kts",
                "app/src/main/AndroidManifest.xml",
                "README.md",
                "PROJECT_MANIFEST.json",
            ]
        if project_type in {"python_cli", "python_simple_app"}:
            return ["README.md", "main.py", "requirements.txt", "PROJECT_MANIFEST.json"]
        if project_type == "python_fastapi":
            return ["README.md", "requirements.txt", "app/main.py", "PROJECT_MANIFEST.json"]
        if project_type == "static_web":
            return ["README.md", "index.html", "style.css", "script.js", "PROJECT_MANIFEST.json"]
        return ["README.md", "PROJECT_MANIFEST.json"]

    def _try_optional_build_or_syntax(
        self,
        request: ProjectGenerationRequest,
        run_id: str,
        workspace_id: str,
        task_id: str,
        project_root: str,
        project_type: ProjectType,
    ) -> str | None:
        if not request.build_if_possible:
            return "Build/test nao solicitado."
        if project_type == "android_kotlin":
            return "Build Android nao executado porque a factory nao garante Android SDK/Gradle no ambiente de sandbox."
        if project_type in {"python_cli", "python_simple_app", "python_fastapi"}:
            compile_target = "app/main.py" if project_type == "python_fastapi" else "main.py"
            result = self.gateway.invoke(
                request.requesting_agent_id,
                run_id,
                "sandbox_run_shell",
                ToolInvocationCreateRequest(
                    sandbox_workspace_id=workspace_id,
                    sandbox_task_id=task_id,
                    cwd_inside_sandbox=project_root,
                    operation_scope="sandbox",
                    operation_type="sandbox_project_syntax_check",
                    input={"command": f"python -m py_compile {compile_target}", "category": "build_shell"},
                    metadata_sanitized={"project_generation_id": request.project_generation_id},
                ),
            )
            if result.status != "succeeded" or result.output.get("status") == "failed":
                return "Python syntax check nao passou; revisar stderr sanitizado no Debugger."
        return None

    def _final_answer(self, *, project_name: str, zip_name: str, artifact_id: str | None, errors: list[str], warnings: list[str]) -> str:
        if errors and not artifact_id:
            return f"Tentei gerar {project_name}, mas o artifact nao ficou pronto. Motivo principal: {errors[0]}."
        if artifact_id:
            suffix = " Ha warnings documentados nos detalhes." if warnings else ""
            return f"Projeto {project_name} gerado no sandbox. Artifact pronto: {zip_name}. Artifact ID: {artifact_id}.{suffix}"
        return f"Projeto {project_name} gerado sem artifact solicitado."

    def _safe_slug(self, value: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
        return safe or "sandbox_project"

    def _safe_filename(self, value: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(value).name).strip("._")
        return safe or "sandbox_project.zip"
