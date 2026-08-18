from __future__ import annotations

from fastapi import APIRouter, Request

from aipinho import __version__
from aipinho.core.paths import PATHS
from aipinho.registries.role_registry import RoleRegistry
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.roles.role_registry_service import RoleRegistryService
from aipinho.registries.route_registry import RouteRegistry
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.artifacts.artifact_writer_preview_service import ArtifactWriterPreviewService
from aipinho.services.artifacts.artifact_write_execution_service import ArtifactWriteExecutionService
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.supervisor.service_manifest_service import ServiceManifestService
from aipinho.services.supervisor.supervisor_core import ADBReverseService, ConnectionProfileService, MonitorStatusBuilder
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.debugger.debugger_status_service import DebuggerStatusService
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.evals.evaluation_workbench_service import EvaluationWorkbenchService
from aipinho.services.interpreter.interpreter_service import InterpreterService
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.manual_inference_status_service import ManualInferenceStatusService
from aipinho.services.models.real_inference_gate_service import RealInferenceGateService
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.curated_memory_service import CuratedMemoryService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.models.model_status_service import ModelStatusService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.rag.retrieval_status_service import RetrievalStatusService
from aipinho.services.rag.integration.rag_memory_status_service import RAGMemoryStatusService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.vision.vision_status_service import VisionStatusService
from aipinho.services.roles.role_model_status_service import RoleModelStatusService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.health_semantics_service import HealthSemanticsService
from aipinho.services.session.session_service import SessionService
from aipinho.services.speaker.speaker_service import SpeakerService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService
from aipinho.services.tools.tool_dry_run_executor import ToolDryRunExecutor
from aipinho.services.tools.tool_registry_service import ToolRegistryService
from aipinho.services.validation.validation_gate_service import ValidationGateService
from aipinho.utils.diagnostics import critical_config_status
from aipinho.utils.yaml_loader import load_yaml_file

from aipinho.services.events.event_core import EventStatusService
from aipinho.services.interaction.interaction_core import InteractionCockpitStatusService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactInteractionStatusService
from aipinho.services.realtime.realtime_core import RealtimeEventBus
from aipinho.services.policy.decision_ownership_service import DecisionOwnershipService
from aipinho.services.context.context_core import ContextKernelService, ContextCacheService

router = APIRouter(prefix="/api/v1", tags=["health"])


def _safe_status(factory):
    try:
        return factory()
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


def _identity() -> dict[str, object]:
    data = load_yaml_file(PATHS.config_root / "app" / "identity.yaml", critical=False, root=PATHS.project_root)
    return {
        "app_name": data.get("app_name", "AIpinho"),
        "version": data.get("version", __version__),
        "environment": data.get("environment", "local"),
    }


@router.get("/health")
def get_health() -> dict[str, object]:
    identity = _identity()
    return {
        "status": "ok",
        "service": identity["app_name"],
        "version": identity["version"],
        "runtime": "local",
    }


@router.get("/status")
def get_status(request: Request) -> dict[str, object]:
    identity = _identity()
    config = critical_config_status()
    action_status = _safe_status(lambda: ActionRegistryService().load().status())
    policy_status = _safe_status(lambda: PolicyPrecedenceService().load().status())
    capability_status = _safe_status(lambda: CapabilityRegistryService().load().status())
    roles_status = _safe_status(lambda: RoleRegistry().load().status())
    role_registry_v2_status = _safe_status(lambda: RoleRegistryService().status())
    role_pipeline_status = _safe_status(lambda: RolePipelineService().status())
    role_model_status = _safe_status(lambda: RoleModelStatusService().status())
    route_status = RouteRegistry().status(request.app)
    chat_status = _safe_status(lambda: ChatService().status())
    speaker_status = _safe_status(lambda: SpeakerService().status())
    interpreter_status = _safe_status(lambda: InterpreterService().status())
    session_status = _safe_status(lambda: SessionService().status())
    task_draft_status = _safe_status(lambda: TaskContractDraftService().status())
    preview_status = _safe_status(lambda: TaskPreviewService().status())
    approval_status = _safe_status(lambda: ApprovalService().status())
    artifact_status = _safe_status(lambda: ArtifactWriterPreviewService().status().model_dump())
    artifact_write_status = _safe_status(lambda: ArtifactWriteExecutionService().status().model_dump())
    tool_registry_status = _safe_status(lambda: ToolRegistryService().load().status())
    tool_dry_run_status = _safe_status(lambda: ToolDryRunExecutor().status())
    read_only_execution_status = _safe_status(lambda: ReadOnlyExecutionService().status())
    analysis_status = _safe_status(lambda: ProjectAnalysisService().status())
    report_status = _safe_status(lambda: ProjectReportService().status())
    task_runtime_status = _safe_status(lambda: TaskRuntimeService().status().model_dump())
    validation_status = _safe_status(lambda: ValidationGateService().status())
    patch_planning_status = _safe_status(lambda: PatchPlanningService().status().model_dump())
    patch_quality_status = _safe_status(lambda: PatchQualityGateService().status())
    patch_apply_status = _safe_status(lambda: PatchApplyService().status().model_dump())
    model_registry_status = _safe_status(lambda: ModelRegistryService().status())
    model_status = _safe_status(lambda: ModelStatusService().status())
    provider_registry_status = _safe_status(lambda: ProviderRegistryService().status())
    model_router_status = _safe_status(lambda: ModelRouterService().status())
    model_invocation_status = _safe_status(lambda: ModelInvocationService().status())
    prompt_assembly_status = _safe_status(lambda: PromptAssemblyService().status())
    evaluation_status = _safe_status(lambda: ModelResponseEvaluator().status())
    llama_cpp_status = _safe_status(lambda: LlamaCppStatusService().status().model_dump())
    manual_inference_status = _safe_status(lambda: ManualInferenceStatusService().status().model_dump())
    real_inference_gate_status = _safe_status(lambda: RealInferenceGateService().status())
    chat_model_policy_status = _safe_status(lambda: ChatModelPolicyService().status())
    chat_manual_inference_status = _safe_status(lambda: ChatManualInferenceService().status())
    memory_candidate_status = _safe_status(lambda: MemoryCandidateService().status())
    curated_memory_status = _safe_status(lambda: CuratedMemoryService().status())
    retrieval_status = _safe_status(lambda: RetrievalStatusService().status())
    rag_memory_status = _safe_status(lambda: RAGMemoryStatusService().status())
    vector_rag_status = _safe_status(lambda: VectorRAGStatusService().status())
    vision_status = _safe_status(lambda: VisionStatusService().status())
    debugger_v2_status = _safe_status(lambda: DebuggerStatusService().status())
    eval_workbench_status = _safe_status(lambda: EvaluationWorkbenchService().status())
    supervisor_manifest_status = _safe_status(lambda: ServiceManifestService().status())
    supervisor_status = _safe_status(lambda: MonitorStatusBuilder().status().model_dump())
    token_auth_status = _safe_status(lambda: LocalTokenService().status())
    adb_reverse_status = _safe_status(lambda: ADBReverseService().status())
    event_contract_status = _safe_status(lambda: EventStatusService().status())
    interaction_cockpit_status = _safe_status(lambda: InteractionCockpitStatusService().status())
    artifact_interaction_status = _safe_status(lambda: ArtifactInteractionStatusService().status())
    realtime_sync_status = _safe_status(lambda: RealtimeEventBus().status())
    decision_ownership_status = _safe_status(lambda: DecisionOwnershipService().matrix().model_dump())
    context_kernel_status = _safe_status(lambda: ContextKernelService().status())
    context_cache_status = _safe_status(lambda: ContextCacheService().status())
    statuses = (
        ("action_registry", action_status),
        ("policy_precedence", policy_status),
        ("capability_registry", capability_status),
        ("roles", roles_status),
        ("role_registry_v2", role_registry_v2_status),
        ("role_pipeline", role_pipeline_status),
        ("role_model_status", role_model_status),
        ("routes", route_status),
        ("chat_service", chat_status),
        ("speaker", speaker_status),
        ("interpreter", interpreter_status),
        ("session", session_status),
        ("task_draft", task_draft_status),
        ("preview", preview_status),
        ("approval", approval_status),
        ("artifacts", artifact_status),
        ("artifact_write", artifact_write_status),
        ("tool_registry", tool_registry_status),
        ("tool_dry_run", tool_dry_run_status),
        ("read_only_execution", read_only_execution_status),
        ("analysis", analysis_status),
        ("reports", report_status),
        ("task_runtime", task_runtime_status),
        ("validation_gate", validation_status),
        ("patch_planning", patch_planning_status),
        ("patch_quality", patch_quality_status),
        ("patch_apply", patch_apply_status),
        ("model_registry", model_registry_status),
        ("model_status", model_status),
        ("provider_registry", provider_registry_status),
        ("model_router", model_router_status),
        ("model_invocation", model_invocation_status),
        ("prompt_assembly", prompt_assembly_status),
        ("model_response_evaluation", evaluation_status),
        ("llama_cpp", llama_cpp_status),
        ("manual_inference", manual_inference_status),
        ("real_inference_gate", real_inference_gate_status),
        ("chat_model_policy", chat_model_policy_status),
        ("chat_manual_inference", chat_manual_inference_status),
        ("memory_candidate", memory_candidate_status),
        ("curated_memory", curated_memory_status),
        ("retrieval", retrieval_status),
        ("rag_memory_integration", rag_memory_status),
        ("vector_rag", vector_rag_status),
        ("vision", vision_status),
        ("debugger_v2", debugger_v2_status),
        ("eval_workbench", eval_workbench_status),
        ("supervisor_manifest", supervisor_manifest_status),
        ("supervisor", supervisor_status),
        ("token_auth", token_auth_status),
        ("adb_reverse", adb_reverse_status),
        ("event_contract_registry", event_contract_status),
        ("interaction_cockpit", interaction_cockpit_status),
        ("artifact_interaction", artifact_interaction_status),
        ("realtime_sync", realtime_sync_status),
        ("decision_ownership", decision_ownership_status),
        ("context_kernel", context_kernel_status),
        ("context_cache", context_cache_status),
    )
    healthy_statuses = {"ok", "disabled", "available", "healthy"}
    tolerated_optional_statuses = {
        "manual_inference": {"disabled"},
        "llama_cpp": {"available", "disabled"},
        "supervisor": {"healthy"},
    }

    warnings = list(config.get("warnings", []))
    for label, status in statuses:
        value = status.get("status")
        if value in healthy_statuses or value in tolerated_optional_statuses.get(label, set()):
            continue
        if value != "ok":
            warnings.append(f"{label}: {status.get('status')}")
    return {
        "status": "ok" if not warnings else "degraded",
        "app_name": identity["app_name"],
        "version": identity["version"],
        "environment": identity["environment"],
        "components": {
            "config": config["status"],
            "policy": "ok" if action_status.get("status") == policy_status.get("status") == capability_status.get("status") == "ok" else "degraded",
            "roles": roles_status.get("status"),
            "role_registry_v2": role_registry_v2_status.get("status"),
            "role_pipeline": role_pipeline_status.get("status"),
            "role_model_status": role_model_status.get("status"),
            "role_model_inference_enabled": bool(role_model_status.get("enabled", False)),
            "controlled_role_inference_enabled": bool(role_model_status.get("enabled", False)),
            "chat_auto_role_inference": bool(role_model_status.get("chat_auto_role_inference", False)),
            "default_coding_role": role_model_status.get("default_coding_role"),
            "default_coding_model": role_model_status.get("default_coding_model"),
            "large_models_manual_only": bool(role_model_status.get("large_models_manual_only", True)),
            "role_model_tool_calling_enabled": bool(role_model_status.get("tool_calling_enabled", False)),
            "role_model_workspace_write_enabled": bool(role_model_status.get("workspace_write_enabled", False)),
            "role_model_vision_runtime_enabled": bool(role_model_status.get("vision_runtime_enabled", False)),
            "role_model_ocr_runtime_enabled": bool(role_model_status.get("ocr_runtime_enabled", False)),
            "role_model_embedding_runtime_enabled": bool(role_model_status.get("embedding_runtime_enabled", False)),
            "role_model_reranker_runtime_enabled": bool(role_model_status.get("reranker_runtime_enabled", False)),
            "routes": route_status.get("status"),
            "chat_service": chat_status.get("status"),
            "speaker": speaker_status.get("status"),
            "interpreter": interpreter_status.get("status"),
            "session": session_status.get("status"),
            "task_draft": task_draft_status.get("status"),
            "preview": preview_status.get("status"),
            "approval": approval_status.get("status"),
            "artifacts": artifact_status.get("status"),
            "artifact_write": artifact_write_status.get("status"),
            "tool_registry": tool_registry_status.get("status"),
            "tool_dry_run": tool_dry_run_status.get("status"),
            "read_only_execution": read_only_execution_status.get("status"),
            "analysis": analysis_status.get("status"),
            "reports": report_status.get("status"),
            "task_runtime": task_runtime_status.get("status"),
            "validation_gate": validation_status.get("status"),
            "patch_planning": patch_planning_status.get("status"),
            "patch_quality": patch_quality_status.get("status"),
            "patch_apply": patch_apply_status.get("status"),
            "model_registry": model_registry_status.get("status"),
            "model_status": model_status.get("status"),
            "provider_registry": provider_registry_status.get("status"),
            "model_router": model_router_status.get("status"),
            "model_invocation": model_invocation_status.get("status"),
            "prompt_assembly": prompt_assembly_status.get("status"),
            "model_response_evaluation": evaluation_status.get("status"),
            "llama_cpp": llama_cpp_status.get("status"),
            "manual_inference": manual_inference_status.get("status"),
            "real_inference_gate": real_inference_gate_status.get("status"),
            "chat_model_policy": chat_model_policy_status.get("status"),
            "chat_manual_inference": chat_manual_inference_status.get("status"),
            "memory_candidate": memory_candidate_status.get("status"),
            "curated_memory": curated_memory_status.get("status"),
            "retrieval": retrieval_status.get("status"),
            "rag_memory_integration": rag_memory_status.get("status"),
            "vector_rag": vector_rag_status.get("status"),
            "vision": vision_status.get("status"),
            "service_manifest": supervisor_manifest_status.get("status"),
            "supervisor": supervisor_status.get("status"),
            "monitor_port": 9099,
            "bootstrap_control_port": 9080,
            "monitor_exclusive": True,
            "launcher_controls_monitor": True,
            "mobile_restart_allowed_ports": [9088, 9089, 9098],
            "mobile_restart_blocked_ports": [9099],
            "mobile_monitor_restart_via_bootstrap": True,
            "token_auth_enabled": True,
            "token_configured": bool(token_auth_status.get("token_configured", False)),
            "adb_reverse_supported": True,
            "wifi_lan_supported": True,
            "tailscale_supported": True,
            "debugger_v2": debugger_v2_status.get("status"),
            "debugger_v2_read_only": bool(debugger_v2_status.get("read_only", True)),
            "debugger_raw_hidden_by_default": bool(debugger_v2_status.get("raw_hidden_by_default", True)),
            "eval_workbench": eval_workbench_status.get("status"),
            "eval_workbench_read_only": bool(eval_workbench_status.get("read_only", True)),
            "vision_runtime_enabled": bool(vision_status.get("vision_runtime_enabled", False)),
            "ocr_runtime_enabled": bool(vision_status.get("ocr_runtime_enabled", False)),
            "vision_rag_enabled": bool(vision_status.get("vision_rag_enabled", False)),
            "ocr_rag_enabled": bool(vision_status.get("ocr_rag_enabled", False)),
            "vector_rag_enabled": bool(vector_rag_status.get("enabled", False)),
            "vector_rag_embedding_runtime_enabled": bool(vector_rag_status.get("embedding_runtime_enabled", False)),
            "vector_rag_reranker_runtime_enabled": bool(vector_rag_status.get("reranker_runtime_enabled", False)),
            "vector_rag_embedding_model": vector_rag_status.get("embedding_model"),
            "vector_rag_reranker_model": vector_rag_status.get("reranker_model"),
            "vector_rag_auto_ingest_enabled": bool(vector_rag_status.get("auto_ingest_enabled", False)),
            "vector_rag_legacy_vectorstore_enabled": bool(vector_rag_status.get("legacy_vectorstore_enabled", False)),
            "role_namespaces_enabled": bool(vector_rag_status.get("role_namespaces_enabled", False)),
            "global_namespace_enabled": bool(vector_rag_status.get("global_namespace_enabled", False)),
            "memory_candidate_enabled": bool(memory_candidate_status.get("memory_candidate_enabled", False)),
            "curated_memory_enabled": bool(curated_memory_status.get("curated_memory_enabled", False)),
            "approved_memory_enabled": bool(curated_memory_status.get("approved_memory_enabled", False)),
            "retrieval_enabled": bool(retrieval_status.get("retrieval_enabled", False)),
            "retrieval_mode": retrieval_status.get("retrieval_mode"),
            "vectorstore_enabled": False,
            "vectorstore_creation_enabled": False,
            "embeddings_enabled": False,
            "rag_enabled": bool(retrieval_status.get("retrieval_enabled", False)),
            "auto_ingest_enabled": False,
            "legacy_vectorstore_enabled": False,
            "chat_auto_retrieval_enabled": False,
            "prompt_auto_injection_enabled": False,
            "context_admission_required": True,
            "context_injection_plan_required": True,
            "rag_memory_integration_enabled": bool(rag_memory_status.get("integration_enabled", False)),
            "auto_prompt_memory_enabled": False,
            "auto_chat_memory_enabled": False,
            "registered_local_models": model_status.get("registered_local_models"),
            "local_model_chat_use_enabled": False,
            "local_model_role_use_enabled": bool(role_model_status.get("enabled", False)),
            "event_contract_registry": event_contract_status.get("status"),
            "event_contracts_loaded": event_contract_status.get("contracts_loaded"),
            "interaction_cockpit": interaction_cockpit_status.get("status"),
            "chat_persistence": bool(interaction_cockpit_status.get("chat_persistence", False)),
            "artifact_links": artifact_interaction_status.get("status"),
            "zip_download_links": bool(artifact_interaction_status.get("zip_enabled", False)),
            "upload_enabled": True,
            "realtime_sync": realtime_sync_status.get("status"),
            "mobile_launcher_sync_via_backend": True,
            "raw_sanitized_hidden_by_default": True,
            "speaker_event_sourced": bool(interaction_cockpit_status.get("speaker_event_sourced", False)),
            "auto_model_execution_from_chat": False,
            "auto_patch_from_chat": False,
            "decision_ownership": decision_ownership_status.get("status"),
            "desktop_launcher_ui_enabled": True,
            "dashboard_tab_enabled": True,
            "chat_tab_enabled": True,
            "pipeline_tab_enabled": True,
            "debugger_tab_enabled": True,
            "settings_tab_enabled": True,
            "event_contract_rendering_enabled": True,
            "restart_allowed_ports": [9088, 9089, 9098],
            "restart_blocked_ports": [9099],
            "token_redaction_enabled": True,
            "direct_service_imports_for_ui_state": False,
            "unknown_event_normal_rendering": False,
            "context_kernel": context_kernel_status.get("status"),
            "context_kernel_enabled": bool(context_kernel_status.get("enabled", False)),
            "context_admission_owner": context_kernel_status.get("context_admission_owner"),
            "context_bundle_builder_enabled": bool(context_kernel_status.get("context_bundle_builder_enabled", False)),
            "context_cache_enabled": bool(context_kernel_status.get("context_cache_enabled", False)),
            "smart_chunks_enabled": bool(context_kernel_status.get("smart_chunks_enabled", False)),
            "safe_for_prompt_required": bool(context_kernel_status.get("safe_for_prompt_required", True)),
            "raw_context_blocked": bool(context_kernel_status.get("raw_context_blocked", True)),
            "citations_required_for_contextual_claims": bool(context_kernel_status.get("citations_required_for_contextual_claims", True)),
        },
        "warnings": warnings,
    }


@router.get("/health/semantics")
def get_health_semantics() -> dict[str, object]:
    return HealthSemanticsService().status()











