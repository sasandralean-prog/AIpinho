from __future__ import annotations

from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.project_generation import ProjectGenerationRequest
from aipinho.schemas.sandbox_autopilot import (
    SandboxAutopilotRequest,
    SandboxAutopilotResult,
    SandboxAutopilotRouteDecision,
)
from aipinho.services.sandbox.sandbox_project_factory import SandboxProjectFactory
from aipinho.schemas.skills.skill_packs import SkillPackSelectionRequest
from aipinho.services.skills.skill_pack_registry_service import SkillPackRegistry
from aipinho.services.workspaces.external_workspace_service import ExternalWorkspaceService


class SandboxAutopilotService:
    def __init__(
        self,
        *,
        project_factory: SandboxProjectFactory | None = None,
        external_workspaces: ExternalWorkspaceService | None = None,
        skill_packs: SkillPackRegistry | None = None,
    ) -> None:
        self.project_factory = project_factory or SandboxProjectFactory()
        self.external_workspaces = external_workspaces or ExternalWorkspaceService()
        self.skill_packs = skill_packs or SkillPackRegistry()

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "mode": "sandbox_autopilot",
            "execution_model": "governed",
            "project_factory_enabled": True,
            "side_effect_scope": "sandbox_only",
            "requires_artifact_token": True,
            "blocked_capabilities": [
                "external_workspace_write_without_contract",
                "network_shell",
                "destructive_shell",
                "git_write",
                "path_escape",
            ],
        }

    def route(self, request: SandboxAutopilotRequest) -> SandboxAutopilotRouteDecision:
        factory_decision = self.project_factory.classify_goal(request.user_goal)
        external_candidates = self.external_workspaces.detect(prompt=request.user_goal)
        if external_candidates:
            return SandboxAutopilotRouteDecision(
                autopilot_run_id=request.autopilot_run_id,
                status="blocked",
                route_type="external_path_onboarding_required",
                recommended_skills=[
                    "external_path_detector",
                    "workspace_onboarding_assistant",
                    "source_readonly_inventory",
                    "workspace_import_preview",
                    "sandbox_safe_alternative_explainer",
                ],
                project_type=request.project_type if request.project_type != "unknown" else factory_decision.project_type,
                project_name=request.project_name or factory_decision.project_name,
                use_sandbox=False,
                requires_workspace=True,
                safe_alternative="A operacao precisa de workspace registrado. Registre o caminho como source_readonly, importe uma copia para sandbox ou crie uma alternativa sandbox sem ler a fonte externa.",
                risk_level="medium",
                reasons=[*factory_decision.reasons, "external_workspace_onboarding_required"],
                evidence_refs=[*factory_decision.evidence_refs, *(ref for item in external_candidates for ref in item.evidence_refs)],
            )
        recommended_skills = self._recommended_skills(factory_decision.route_type, factory_decision.project_type)
        recommended_packs = self._recommended_packs(request.user_goal, request.requesting_agent_id, factory_decision.project_type, recommended_skills)
        risk_level = "low" if factory_decision.use_sandbox and not factory_decision.requires_workspace else "medium"
        return SandboxAutopilotRouteDecision(
            autopilot_run_id=request.autopilot_run_id,
            status=factory_decision.status,
            route_type=factory_decision.route_type,
            recommended_skills=recommended_skills,
            project_type=request.project_type if request.project_type != "unknown" else factory_decision.project_type,
            project_name=request.project_name or factory_decision.project_name,
            use_sandbox=factory_decision.use_sandbox,
            requires_workspace=factory_decision.requires_workspace,
            safe_alternative=factory_decision.safe_alternative,
            risk_level=risk_level,
            reasons=[*factory_decision.reasons, "autopilot_recommendation_only" if request.dry_run else "autopilot_governed_execution", *(f"skill_pack_selected:{item}" for item in recommended_packs)],
            evidence_refs=[*factory_decision.evidence_refs, f"autopilot:{request.autopilot_run_id}"],
        )

    def run(self, request: SandboxAutopilotRequest) -> SandboxAutopilotResult:
        started_at = utc_now_iso()
        route = self.route(request)
        if request.dry_run:
            return SandboxAutopilotResult(
                autopilot_run_id=request.autopilot_run_id,
                status="routed",
                route_decision=route,
                final_answer_sanitized="Autopilot preparado em dry-run. Nenhum arquivo foi criado.",
                evidence_refs=route.evidence_refs,
                started_at=started_at,
                completed_at=utc_now_iso(),
                metadata_sanitized={"dry_run": True},
            )
        if route.requires_workspace and not route.use_sandbox:
            return SandboxAutopilotResult(
                autopilot_run_id=request.autopilot_run_id,
                status="blocked",
                route_decision=route,
                final_answer_sanitized=route.safe_alternative or "A operacao precisa de workspace registrado antes de executar.",
                errors=["external_workspace_onboarding_required" if route.route_type == "external_path_onboarding_required" else "external_workspace_required"],
                evidence_refs=route.evidence_refs,
                started_at=started_at,
                completed_at=utc_now_iso(),
                metadata_sanitized={"blocked_reason": "external_workspace_onboarding_required" if route.route_type == "external_path_onboarding_required" else "external_workspace_required"},
            )

        project_request = ProjectGenerationRequest(
            sandbox_workspace_id=request.sandbox_workspace_id,
            session_id=request.session_id,
            requesting_agent_id=request.requesting_agent_id,
            user_goal=request.user_goal,
            project_name=request.project_name or route.project_name,
            project_type=request.project_type if request.project_type != "unknown" else route.project_type,
            requested_assets=request.requested_assets,
            requested_features=request.requested_features,
            output_zip_name=request.output_zip_name,
            metadata_sanitized={
                **request.metadata_sanitized,
                "autopilot_run_id": request.autopilot_run_id,
                "autopilot_mode": "sandbox_autopilot",
                "recommended_skills": route.recommended_skills,
                "recommended_skill_packs": [
                    reason.split(":", 1)[1]
                    for reason in route.reasons
                    if reason.startswith("skill_pack_selected:")
                ],
            },
        )
        generation = self.project_factory.generate(project_request)
        status = generation.status
        validation_status = "passed" if generation.validation_ids and not generation.errors else "failed" if generation.errors else "unknown"
        final_answer = generation.final_answer_sanitized
        if generation.status == "completed_with_warnings":
            final_answer = f"{final_answer} Autopilot concluiu com warnings nao bloqueantes."
        return SandboxAutopilotResult(
            autopilot_run_id=request.autopilot_run_id,
            status=status,
            route_decision=route,
            project_generation=generation,
            artifact_ids=generation.artifact_ids,
            zip_artifact_id=generation.zip_artifact_id,
            download_endpoint=generation.download_endpoint,
            requires_token=generation.requires_token,
            validation_status=validation_status,
            final_answer_sanitized=final_answer,
            warnings=generation.warnings,
            errors=generation.errors,
            evidence_refs=[*route.evidence_refs, *generation.evidence_refs],
            started_at=started_at,
            completed_at=utc_now_iso(),
            metadata_sanitized={
                "project_generation_id": generation.project_generation_id,
                "sandbox_task_id": generation.sandbox_task_id,
                "correction_loop_count": 0,
                "autopilot_used_project_factory": True,
            },
        )

    def _recommended_skills(self, route_type: str, project_type: str) -> list[str]:
        if route_type == "external_path_requires_workspace":
            return ["workspace_registry_checker", "sandbox_safe_alternative_explainer"]
        base = ["sandbox_project_generator"]
        if project_type == "android_kotlin":
            base.extend(["sandbox_android_kotlin_game_generator", "sandbox_asset_placeholder_generator"])
        elif project_type in {"python_cli", "python_simple_app"}:
            base.append("sandbox_python_project_generator")
        elif project_type == "static_web":
            base.append("sandbox_static_web_project_generator")
        else:
            base.append("sandbox_generic_files_generator")
        base.extend(["sandbox_zip_exporter", "artifact_reliability_validator"])
        return base

    def _recommended_packs(self, user_goal: str, agent_id: str, project_type: str, recommended_skills: list[str]) -> list[str]:
        selection = self.skill_packs.select(
            SkillPackSelectionRequest(
                user_goal=user_goal,
                agent_id="autopilot" if agent_id not in {"aipinho", "lucio", "codex", "gemini", "autopilot"} else agent_id,
                project_stack="android_gradle" if project_type == "android_kotlin" else "python" if project_type in {"python_cli", "python_simple_app"} else "mixed",
                requested_capabilities=recommended_skills,
                execution_mode="sandbox_autopilot",
            )
        )
        return [candidate.skill_pack_id for candidate in selection.candidates[:3]]
