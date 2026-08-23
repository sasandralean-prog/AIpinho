from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.pinhoforge_bridge import PinhoForgeBridgeRequest
from aipinho.schemas.pinhoforge_bridge.android_workbench import PinhoForgeAndroidWorkbenchRequest
from aipinho.schemas.pinhoforge_bridge.command_catalog import PinhoForgeCommandCatalogQuery, PinhoForgeCommandPreviewRequest
from aipinho.schemas.pinhoforge_bridge.conversion import PinhoForgeConversionRequest
from aipinho.schemas.pinhoforge_bridge.hardware_profiler import PinhoForgeHardwareProfilerRequest
from aipinho.schemas.pinhoforge_bridge.governed_terminal import PinhoForgeTerminalCancelRequest, PinhoForgeTerminalExecuteRequest, PinhoForgeTerminalPreviewRequest
from aipinho.schemas.pinhoforge_bridge.media_3d import PinhoForge3DRequest, PinhoForgeImageOperationSpec, PinhoForgeImageRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.pinhoforge_bridge import (
    PinhoForgeAndroidWorkbenchProvider,
    PinhoForge3DProvider,
    PinhoForgeBridgeClient,
    PinhoForgeBridgeConfigService,
    PinhoForgeBridgePolicyService,
    PinhoForgeCommandCatalogProvider,
    PinhoForgeConversionProvider,
    PinhoForgeGovernedTerminalProvider,
    PinhoForgeHardwareProfilerProvider,
    PinhoForgeImageProvider,
    PinhoForgeManifestReader,
)


def _manifest_payload() -> dict:
    return {
        "schema_version": 1,
        "provider_id": "pinhoforge_studio",
        "generated_at": "2026-01-01T00:00:00Z",
        "app_name": "PinhoForgeStudio2",
        "bridge_mode": "discovery_only",
        "execution_enabled": False,
        "modules": [
            {
                "module_id": "conversion",
                "category": "conversion",
                "capability_count": 1,
                "status": "available",
                "execution_enabled": False,
                "notes": ["discovery_only"],
            }
        ],
        "capabilities": [
            {
                "capability_id": "conversion_dry_run",
                "display_name": "Dry-run de conversao",
                "category": "conversion",
                "risk_level": "safe",
                "status": "available",
                "experimental": False,
                "supports_dry_run": True,
                "supports_batch": True,
                "supports_artifacts": False,
                "requires_external_tool": False,
                "required_tools": [],
                "execution_enabled": False,
                "limitations": ["bridge_execution_disabled_until_governed_execution_sprint"],
                "tags": ["converter", "dry-run"],
            }
        ],
        "external_tools": [],
        "warnings": ["bridge_execution_blocked_by_design"],
        "evidence_refs": ["test_manifest"],
    }


def _config(tmp_path: Path, manifest_path: Path | None) -> Path:
    config = tmp_path / "pinhoforge_bridge.yaml"
    manifest_value = json.dumps(str(manifest_path)) if manifest_path else "null"
    config.write_text(
        f"""
version: 1
runtime:
  enabled: true
  provider_id: pinhoforge_studio
  transport: local_manifest_file
  manifest_path: {manifest_value}
  execution_enabled: false
  require_local_auth: true
  allowed_operations:
    - handshake
    - health
    - manifest
    - readiness
  blocked_operations:
    - execute
""",
        encoding="utf-8",
    )
    return config


def _service(tmp_path: Path) -> PinhoForgeBridgeClient:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest_payload()), encoding="utf-8")
    return PinhoForgeBridgeClient(config_service=PinhoForgeBridgeConfigService(_config(tmp_path, manifest_path), root=tmp_path))


def test_manifest_reader_loads_discovery_only_provider(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest_payload()), encoding="utf-8")

    status = PinhoForgeManifestReader().status(manifest_path)

    assert status.status == "ready_for_discovery"
    assert status.manifest_loaded is True
    assert status.execution_enabled is False
    assert status.capability_count == 1
    assert status.blocked_operations == ["execute"]


def test_invalid_manifest_returns_structured_status(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{not json", encoding="utf-8")

    status = PinhoForgeManifestReader().status(manifest_path)

    assert status.status == "invalid_manifest"
    assert status.manifest_loaded is False
    assert "pinhoforge_manifest_invalid" in status.errors


def test_policy_allows_only_readonly_bridge_operations() -> None:
    policy = PinhoForgeBridgePolicyService(execution_enabled=False)

    health = policy.evaluate("health")
    execute = policy.evaluate("execute")

    assert health.decision == "allow"
    assert execute.decision == "deny"
    assert execute.reason_code == "pinhoforge_bridge_execution_disabled"


def test_client_handshake_and_readiness_are_token_safe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PINHOFORGE_BRIDGE_TOKEN", "secret-local-token")
    client = _service(tmp_path)

    handshake = client.request(PinhoForgeBridgeRequest(operation="handshake"))
    readiness = client.request(PinhoForgeBridgeRequest(operation="readiness"))
    serialized = json.dumps({"handshake": handshake.model_dump(), "readiness": readiness.model_dump()})

    assert handshake.status == "ok"
    assert readiness.status == "ok"
    assert handshake.execution_enabled is False
    assert "secret-local-token" not in serialized


def test_client_blocks_execute_without_side_effects(tmp_path: Path) -> None:
    client = _service(tmp_path)

    response = client.request(PinhoForgeBridgeRequest(operation="execute"))

    assert response.status == "blocked"
    assert response.execution_enabled is False
    assert response.policy_decision is not None
    assert response.policy_decision.reason_code == "pinhoforge_bridge_execution_disabled"


def test_conversion_provider_lists_capabilities_and_dry_runs_without_artifact() -> None:
    provider = PinhoForgeConversionProvider()

    capabilities = provider.list_capabilities("req-cap")
    dry_run = provider.dry_run(
        PinhoForgeConversionRequest(
            request_id="req-dry",
            operation="dry_run",
            source_scope="registered_workspace",
            detected_format="image-png",
            target_format="image-jpeg",
        )
    )

    assert capabilities.status == "completed"
    assert capabilities.capabilities
    assert dry_run.status == "preview_created"
    assert dry_run.dry_run is not None
    assert dry_run.dry_run["created_output"] is False
    assert dry_run.artifact is None


def test_conversion_provider_requires_validated_output_for_execution(tmp_path: Path) -> None:
    provider = PinhoForgeConversionProvider()
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"
    input_path.write_bytes(b"input")
    output_path.write_bytes(b"converted")

    result = provider.execute(
        PinhoForgeConversionRequest(
            request_id="req-execute",
            operation="execute",
            source_scope="registered_workspace",
            input_path=str(input_path),
            bridge_output_path=str(output_path),
            requested_output_name="converted.jpg",
            detected_format="image-png",
            target_format="image-jpeg",
        )
    )

    assert result.status == "completed"
    assert result.artifact is not None
    assert result.artifact.filename == "converted.jpg"
    assert result.artifact.size_bytes == len(b"converted")
    assert result.artifact.requires_token is True


def test_command_catalog_search_preview_and_execution_block() -> None:
    provider = PinhoForgeCommandCatalogProvider()

    search = provider.search(PinhoForgeCommandCatalogQuery(request_id="req-search", query="path"))
    preview = provider.preview(PinhoForgeCommandPreviewRequest(request_id="req-preview", command_id="ps-test-path", parameters={"PATH": "C:\\Temp"}))
    blocked = provider.execute_blocked("req-exec")

    assert search.status == "completed"
    assert search.results
    assert all(item["execution_enabled"] is False for item in search.results)
    assert preview.status == "preview_created"
    assert preview.preview is not None
    assert preview.preview["execution_enabled"] is False
    assert blocked.status == "blocked"
    assert blocked.reason_code == "command_catalog_execution_disabled"


def test_command_catalog_blocks_injection_and_dangerous_by_default() -> None:
    provider = PinhoForgeCommandCatalogProvider()

    search = provider.search(PinhoForgeCommandCatalogQuery(request_id="req-safe", query=""))
    injection = provider.preview(
        PinhoForgeCommandPreviewRequest(
            request_id="req-injection",
            command_id="ps-test-path",
            parameters={"PATH": "safe; Remove-Item -Recurse C:\\"},
        )
    )

    assert all(item["risk"] != "dangerous" for item in search.results)
    assert injection.status == "blocked"
    assert injection.reason_code == "command_parameter_injection_blocked"


def test_tool_gateway_registers_validated_conversion_output_as_artifact(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Bridge"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_conversion", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"
    input_path.write_bytes(b"input")
    output_path.write_bytes(b"converted")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_conversion_execute",
        ToolInvocationCreateRequest(
            input={
                "source_scope": "registered_workspace",
                "input_path": str(input_path),
                "bridge_output_path": str(output_path),
                "requested_output_name": "converted.jpg",
                "detected_format": "image-png",
                "target_format": "image-jpeg",
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.artifacts
    assert result.output["artifact"]["artifact_id"] == result.artifacts[0].artifact_id
    assert result.output["artifact"]["requires_token"] is True


def test_tool_gateway_command_catalog_search_is_read_only(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Bridge"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_command_catalog", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_command_search",
        ToolInvocationCreateRequest(input={"query": "path"}),
    )

    assert result.status == "succeeded"
    assert result.output["status"] == "completed"
    assert result.output["results"]
    assert all(item["execution_enabled"] is False for item in result.output["results"])


def test_hardware_profiler_returns_readiness_summary(monkeypatch) -> None:
    monkeypatch.setenv("ANDROID_HOME", "C:\\Android\\Sdk")
    provider = PinhoForgeHardwareProfilerProvider()

    result = provider.handle(PinhoForgeHardwareProfilerRequest(operation="get_readiness_summary"))

    assert result.status in {"completed", "completed_with_warnings"}
    assert result.readiness_summary is not None
    assert result.readiness_summary.android_readiness in {"ready", "partial", "missing", "degraded"}


def test_hardware_profiler_blocks_environment_mutation() -> None:
    provider = PinhoForgeHardwareProfilerProvider()

    result = provider.handle(PinhoForgeHardwareProfilerRequest(operation="repair_environment"))

    assert result.status == "blocked"
    assert result.reason_code == "pinhoforge_environment_mutation_not_allowed"


def test_missing_ffmpeg_marks_conversion_degraded(monkeypatch) -> None:
    def fake_discover(command: str, *, tool_id: str, **kwargs):
        from aipinho.capabilities.media_metadata.environment import MediaToolDiscoveryResult

        return MediaToolDiscoveryResult(
            tool_id=tool_id,
            command=command,
            status="unavailable",
            reason_code=f"{tool_id.upper()}_NOT_AVAILABLE",
        )

    def fake_which(name: str) -> str | None:
        mapping = {
            "java": "C:\\Tools\\java.exe",
            "gradle": "C:\\Tools\\gradle.bat",
            "adb": "C:\\Tools\\adb.exe",
        }
        return mapping.get(name)

    monkeypatch.setattr("aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider.discover_media_tool", fake_discover)
    monkeypatch.setattr("aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider.shutil.which", fake_which)
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    provider = PinhoForgeHardwareProfilerProvider()

    result = provider.handle(PinhoForgeHardwareProfilerRequest(operation="get_readiness_summary"))

    assert result.readiness_summary is not None
    assert result.readiness_summary.conversion_readiness in {"missing", "degraded"}


def test_missing_android_sdk_marks_android_degraded(monkeypatch) -> None:
    def fake_which(name: str) -> str | None:
        mapping = {
            "java": "C:\\Tools\\java.exe",
            "adb": "C:\\Tools\\adb.exe",
            "gradle": "C:\\Tools\\gradle.bat",
        }
        return mapping.get(name)

    monkeypatch.setattr("aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider.shutil.which", fake_which)
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    provider = PinhoForgeHardwareProfilerProvider()

    result = provider.handle(PinhoForgeHardwareProfilerRequest(operation="get_readiness_summary"))

    assert result.readiness_summary is not None
    assert result.readiness_summary.android_readiness in {"missing", "degraded"}


def test_hardware_profiler_redacts_paths(monkeypatch) -> None:
    monkeypatch.setenv("ANDROID_HOME", str(Path.home() / "AppData" / "Local" / "Android" / "Sdk"))
    provider = PinhoForgeHardwareProfilerProvider()

    result = provider.handle(PinhoForgeHardwareProfilerRequest(operation="get_environment_profile"))

    assert result.system_profile is not None
    assert str(Path.home()) not in json.dumps(result.model_dump())
    assert result.redaction_applied is True


def test_tool_gateway_registers_hardware_profiler_report_artifacts(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Bridge Hardware"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_hardware_profile", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_environment_report_export",
        ToolInvocationCreateRequest(input={}),
    )

    assert result.status == "succeeded"
    assert result.output["status"] in {"completed", "completed_with_warnings"}
    assert len(result.artifacts) == 2
    assert all("token=" not in artifact.download_endpoint for artifact in result.artifacts)


def test_android_provider_blocks_unregistered_external_path() -> None:
    provider = PinhoForgeAndroidWorkbenchProvider()

    result = provider.handle(
        PinhoForgeAndroidWorkbenchRequest(
            operation="detect_project",
            project_path="C:\\Outside\\Project",
            source_scope="unknown",
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "android_external_path_unregistered"


def test_android_provider_allows_safe_gradle_task_and_registers_artifacts(tmp_path: Path) -> None:
    project = _android_fixture(tmp_path / "android_project")
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel_android"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Bridge Android"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_android", status="running"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        store=AgentToolInvocationStore(tmp_path / "gateway_android"),
        shell_runner=_FakeShellRunner(),
    )

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_android_gradle_task_execute",
        ToolInvocationCreateRequest(
            input={
                "project_path": str(project),
                "source_scope": "registered_workspace",
                "task_id": "tasks",
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.output["status"] == "completed"
    assert result.output["execution_result"]["exit_code"] == 0
    assert result.artifacts


def test_android_provider_blocks_unknown_gradle_task() -> None:
    provider = PinhoForgeAndroidWorkbenchProvider(runner=_FakeShellRunner())
    project = _android_fixture(Path.cwd() / "tmp_android_unknown")

    result = provider.handle(
        PinhoForgeAndroidWorkbenchRequest(
            operation="execute_gradle_task",
            project_path=str(project),
            source_scope="registered_workspace",
            task_id="publishRelease",
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "android_unknown_gradle_task_blocked"


def test_android_provider_blocks_adb_shell() -> None:
    provider = PinhoForgeAndroidWorkbenchProvider()

    result = provider.handle(PinhoForgeAndroidWorkbenchRequest(operation="adb_shell"))

    assert result.status == "blocked"
    assert result.reason_code == "android_adb_shell_blocked"


def test_android_provider_timeout_is_handled(tmp_path: Path) -> None:
    project = _android_fixture(tmp_path / "android_timeout")
    provider = PinhoForgeAndroidWorkbenchProvider(runner=_TimeoutShellRunner())

    result = provider.handle(
        PinhoForgeAndroidWorkbenchRequest(
            operation="execute_gradle_task",
            project_path=str(project),
            source_scope="registered_workspace",
            task_id="tasks",
        )
    )

    assert result.status == "timeout"
    assert result.execution_result is not None
    assert result.execution_result.status == "timeout"


def test_tool_gateway_registers_media_provider(tmp_path: Path) -> None:
    gateway = AgentToolGatewayService(kernel=AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel")))

    tools = {tool.tool_name for tool in gateway.list_tools(enabled=True)}

    assert "pinhoforge_media_image_operation" in tools


def test_policy_allows_image_edit_for_artifact_input(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Media"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_media_image", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))
    input_path = _binary_fixture(tmp_path / "input_artifact.png", b"png")
    output_path = _binary_fixture(tmp_path / "output_artifact.png", b"out")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_media_image_operation",
        ToolInvocationCreateRequest(
            input={
                "operation": "apply_operations",
                "source_scope": "artifact_library",
                "input_path": str(input_path),
                "bridge_output_path": str(output_path),
                "requested_output_name": "artifact-output.png",
                "output_format": "png",
                "operations": [{"type": "brightness", "parameters": {"delta": "8"}}],
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.output["status"] == "completed"


def test_policy_blocks_external_unregistered_image(tmp_path: Path) -> None:
    provider = PinhoForgeImageProvider()
    input_path = _binary_fixture(tmp_path / "blocked.png", b"in")
    output_path = _binary_fixture(tmp_path / "blocked-out.png", b"out")

    result = provider.handle(
        PinhoForgeImageRequest(
            operation="apply_operations",
            source_scope="unknown",
            input_path=str(input_path),
            bridge_output_path=str(output_path),
            operations=[PinhoForgeImageOperationSpec(type="brightness", parameters={"delta": "1"})],
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "image_external_path_unregistered"


def test_policy_blocks_original_overwrite(tmp_path: Path) -> None:
    provider = PinhoForgeImageProvider()
    input_path = _binary_fixture(tmp_path / "overwrite.png", b"png")

    result = provider.handle(
        PinhoForgeImageRequest(
            operation="export_image",
            source_scope="registered_workspace",
            input_path=str(input_path),
            bridge_output_path=str(input_path),
            requested_output_name="overwrite.png",
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "image_original_overwrite_blocked"


def test_image_provider_registers_artifact(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Media Artifact"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_media_image", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))
    input_path = _binary_fixture(tmp_path / "register.png", b"png")
    output_path = _binary_fixture(tmp_path / "register-copy.png", b"copy")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_media_image_operation",
        ToolInvocationCreateRequest(
            input={
                "operation": "export_image",
                "source_scope": "registered_workspace",
                "input_path": str(input_path),
                "bridge_output_path": str(output_path),
                "requested_output_name": "register-copy.png",
                "output_format": "png",
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.artifacts
    assert result.output["artifact"]["artifact_id"] == result.artifacts[0].artifact_id


def test_image_artifact_ready_requires_file(tmp_path: Path) -> None:
    provider = PinhoForgeImageProvider()
    input_path = _binary_fixture(tmp_path / "missing.png", b"in")

    result = provider.handle(
        PinhoForgeImageRequest(
            operation="generate_report",
            source_scope="registered_workspace",
            input_path=str(input_path),
            bridge_output_path=str(tmp_path / "not-created.png"),
            requested_output_name="report.png",
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "image_artifact_output_missing"


def test_model_review_required_for_semantic_task(tmp_path: Path) -> None:
    provider = PinhoForgeImageProvider()
    input_path = _binary_fixture(tmp_path / "semantic.png", b"in")
    output_path = _binary_fixture(tmp_path / "semantic-out.png", b"out")

    result = provider.handle(
        PinhoForgeImageRequest(
            operation="generate_report",
            source_scope="registered_workspace",
            input_path=str(input_path),
            bridge_output_path=str(output_path),
            requested_output_name="semantic-out.png",
            model_review_policy="required_for_semantic_tasks",
            metadata={"semantic_task": True, "review_goal": "quality"},
        )
    )

    assert result.status == "completed_with_warnings"
    assert result.model_review_recommended is True
    assert result.model_review_result is not None
    assert result.model_review_result["status"] == "review_required_but_unavailable"


def test_tool_gateway_registers_3d_provider(tmp_path: Path) -> None:
    gateway = AgentToolGatewayService(kernel=AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel")))

    tools = {tool.tool_name for tool in gateway.list_tools(enabled=True)}

    assert "pinhoforge_media_3d_operation" in tools


def test_policy_allows_3d_scene_export(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="3D"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_media_3d", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))
    output_path = _binary_fixture(tmp_path / "scene.obj", b"obj")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_media_3d_operation",
        ToolInvocationCreateRequest(
            input={
                "operation": "export_scene",
                "scene_title": "Scene",
                "output_format": "obj",
                "bridge_output_path": str(output_path),
                "requested_output_name": "scene.obj",
                "primitive_specs": [{"type": "cube", "name": "core"}],
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.output["status"] == "completed"
    assert result.artifacts


def test_policy_blocks_external_asset_download(tmp_path: Path) -> None:
    provider = PinhoForge3DProvider()
    output_path = _binary_fixture(tmp_path / "scene.obj", b"obj")

    result = provider.handle(
        PinhoForge3DRequest(
            operation="export_scene",
            scene_title="Scene",
            output_format="obj",
            bridge_output_path=str(output_path),
            primitive_specs=[{"type": "cube", "name": "core"}],
            metadata={"external_asset_download": True},
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "media_external_asset_download_blocked"


def test_debugger_trace_records_media_operation(tmp_path: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel"))
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Trace"))
    run = kernel.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="bridge_media_image", status="running"))
    gateway = AgentToolGatewayService(kernel=kernel, store=AgentToolInvocationStore(tmp_path / "gateway"))
    input_path = _binary_fixture(tmp_path / "trace.png", b"in")
    output_path = _binary_fixture(tmp_path / "trace-out.png", b"out")

    result = gateway.invoke(
        "aipinho",
        run.run_id,
        "pinhoforge_media_image_operation",
        ToolInvocationCreateRequest(
            input={
                "operation": "generate_report",
                "source_scope": "registered_workspace",
                "input_path": str(input_path),
                "bridge_output_path": str(output_path),
                "requested_output_name": "trace-out.png",
                "output_format": "png",
            }
        ),
    )

    assert result.status == "succeeded"
    assert result.output["evidence_refs"]


def test_final_answer_does_not_claim_visual_quality_without_review(tmp_path: Path) -> None:
    provider = PinhoForgeImageProvider()
    input_path = _binary_fixture(tmp_path / "truth.png", b"in")
    output_path = _binary_fixture(tmp_path / "truth-out.png", b"out")

    result = provider.handle(
        PinhoForgeImageRequest(
            operation="export_image",
            source_scope="registered_workspace",
            input_path=str(input_path),
            bridge_output_path=str(output_path),
            requested_output_name="truth-out.png",
            output_format="png",
        )
    )

    assert result.status == "completed"
    assert "melhor" not in result.human_message.lower()
    assert "quality" not in result.human_message.lower()


def test_tool_gateway_registers_terminal_provider(tmp_path: Path) -> None:
    gateway = AgentToolGatewayService(kernel=AgentSessionKernelService(store=AgentSessionStore(tmp_path / "kernel")))

    tools = {tool.tool_name for tool in gateway.list_tools(enabled=True)}

    assert {"pinhoforge_terminal_preview", "pinhoforge_terminal_execute", "pinhoforge_terminal_cancel", "pinhoforge_terminal_status"} <= tools


def test_terminal_preview_blocks_unknown_scope(tmp_path: Path) -> None:
    provider = PinhoForgeGovernedTerminalProvider()
    cwd = tmp_path

    result = provider.preview(
        PinhoForgeTerminalPreviewRequest(
            session_id="sess-blocked",
            command_source="catalog",
            command_id="powershell-files-recursive",
            cwd=str(cwd),
            source_scope="unknown",
        )
    )

    assert result.status == "blocked"
    assert result.reason_code == "terminal_unknown_scope_blocked"


def test_terminal_preview_and_execute_safe_catalog_command(tmp_path: Path) -> None:
    provider = PinhoForgeGovernedTerminalProvider()
    cwd = tmp_path
    (cwd / "hello.txt").write_text("ok", encoding="utf-8")

    preview = provider.preview(
        PinhoForgeTerminalPreviewRequest(
            session_id="sess-safe",
            command_source="catalog",
            command_id="powershell-files-recursive",
            cwd=str(cwd),
            source_scope="sandbox",
        )
    )
    execute = provider.execute(
        PinhoForgeTerminalExecuteRequest(
            preview_id=preview.preview_id,
            expected_outputs=["hello.txt"],
        )
    )

    assert preview.status == "previewed"
    assert preview.requires_approval is False
    assert execute.status == "completed"
    assert execute.output_artifacts


def test_terminal_execute_requires_approval_for_manual_command(tmp_path: Path) -> None:
    provider = PinhoForgeGovernedTerminalProvider()
    cwd = tmp_path

    preview = provider.preview(
        PinhoForgeTerminalPreviewRequest(
            session_id="sess-manual",
            command_source="manual",
            command_line="Get-ChildItem .",
            cwd=str(cwd),
            source_scope="sandbox",
        )
    )
    execute = provider.execute(PinhoForgeTerminalExecuteRequest(preview_id=preview.preview_id))

    assert preview.status == "previewed"
    assert preview.requires_approval is True
    assert execute.status == "blocked"
    assert execute.reason_code == "terminal_approval_required"


def test_terminal_readonly_scope_blocks_write_like_command(tmp_path: Path) -> None:
    provider = PinhoForgeGovernedTerminalProvider()

    preview = provider.preview(
        PinhoForgeTerminalPreviewRequest(
            session_id="sess-readonly",
            command_source="manual",
            command_line="Set-Content .\\report.txt 'x'",
            cwd=str(tmp_path),
            source_scope="registered_workspace_readonly",
        )
    )

    assert preview.status == "blocked"
    assert "source_readonly_write_blocked" in preview.blocked_reasons


def test_terminal_cancel_marks_running_session(tmp_path: Path) -> None:
    provider = PinhoForgeGovernedTerminalProvider(runner=_BlockingTerminalRunner())
    preview = provider.preview(
        PinhoForgeTerminalPreviewRequest(
            session_id="sess-cancel",
            command_source="catalog",
            command_id="powershell-files-recursive",
            cwd=str(tmp_path),
            source_scope="sandbox",
        )
    )

    results: dict[str, object] = {}

    def _run() -> None:
        results["execute"] = provider.execute(PinhoForgeTerminalExecuteRequest(preview_id=preview.preview_id))

    worker = __import__("threading").Thread(target=_run, daemon=True)
    worker.start()
    __import__("time").sleep(0.1)
    cancelled = provider.cancel_execution(PinhoForgeTerminalCancelRequest(session_id="sess-cancel"))
    worker.join(timeout=2.0)

    assert cancelled.status == "cancelling"
    status = provider.session_status("status-check", "sess-cancel")
    assert status.status in {"cancelling", "cancelled"}


def _android_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "settings.gradle.kts").write_text("pluginManagement {}", encoding="utf-8")
    (root / "build.gradle.kts").write_text("plugins {}", encoding="utf-8")
    (root / "gradlew.bat").write_text("@echo off", encoding="utf-8")
    manifest = root / "app" / "src" / "main" / "AndroidManifest.xml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("<manifest package=\"test.app\" />", encoding="utf-8")
    return root


class _FakeShellRunner:
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


class _TimeoutShellRunner:
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, timeout)


def _binary_fixture(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class _BlockingTerminalRunner:
    def run(self, command_line: str, cwd: str, timeout_seconds: int, cancellation) -> dict[str, object]:
        started = __import__("time").monotonic()
        while not cancellation.is_set() and __import__("time").monotonic() - started < 1.5:
            __import__("time").sleep(0.02)
        return {
            "status": "cancelled" if cancellation.is_set() else "completed",
            "reason_code": "terminal_cancelled" if cancellation.is_set() else None,
            "exit_code": None if cancellation.is_set() else 0,
            "stdout": "",
            "stderr": "",
            "duration_ms": int((__import__("time").monotonic() - started) * 1000),
        }
