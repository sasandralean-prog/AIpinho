from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.artifacts.artifact_library import (
    ArtifactContextUseResult,
    ArtifactRecordV2,
)
from aipinho.schemas.context.contracts import (
    ContextBundle,
    ContextEvidenceRef,
    ContextInjectionPlan,
    ContextItem,
    ContextScope,
    ContextSourceRef,
)
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.services.context.context_plan_runtime_service import (
    CanonicalContextPlanStore,
    ContextPlanResolution,
    ContextPlanRuntimeService,
)
from aipinho.services.context.mission_context_handoff_service import (
    MissionContextHandoffService,
)
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.runtime.task_run_context_service import TaskRunContextService
from tests.support.runtime_fixtures import runtime_run


class _NoLegacyPlanner:
    def get_plan(self, _plan_id):
        return None


class _NoLegacyValidator:
    def validate_plan(self, _plan):
        raise AssertionError("legacy validator must not run for canonical plans")


class _BundleRepo:
    def __init__(self, bundle):
        self.bundle = bundle

    def get(self, bundle_id):
        return self.bundle if bundle_id == self.bundle.bundle_id else None


def test_context_plan_runtime_resolves_canonical_bundle_into_evidence_context(
    tmp_path,
):
    source = ContextSourceRef(
        source_type="artifact_record",
        source_id="artifact_diag",
        path="diagnosis.md",
    )
    bundle = ContextBundle(
        request_id="request_test",
        purpose="patch_planning",
        scope=ContextScope(session_id="session_test"),
        items=[
            ContextItem(
                layer="attachments_artifacts",
                source_type="artifact_record",
                source_ref=source,
                summary="diagnosis.md",
                content="Observed codec failure in the governed analysis.",
                content_hash="a" * 64,
                evidence_refs=[
                    ContextEvidenceRef(
                        evidence_id="evidence_diag",
                        source_ref=source,
                        summary="Governed diagnosis evidence.",
                    )
                ],
                trust_level="cited",
                budget_chars=48,
            )
        ],
        safe_for_prompt=True,
    )
    plan = ContextInjectionPlan(
        plan_id="context_plan_test",
        bundle_id=bundle.bundle_id,
        purpose="patch_planning",
        safe_for_prompt_assembly=True,
    )
    store = CanonicalContextPlanStore(root=tmp_path / "plans")
    store.save(plan)
    service = ContextPlanRuntimeService(
        store=store,
        bundles=_BundleRepo(bundle),
        legacy_planner=_NoLegacyPlanner(),
        legacy_validator=_NoLegacyValidator(),
    )

    resolved = service.resolve(plan.plan_id)

    assert resolved.status == "ready"
    assert resolved.source == "context_kernel"
    assert resolved.evidence_context == [
        {
            "evidence_id": "evidence_diag",
            "artifact_id": "artifact_diag",
            "logical_path": "diagnosis.md",
            "content": "Observed codec failure in the governed analysis.",
            "citation_ids": [],
            "source_type": "artifact_record",
        }
    ]


def test_task_run_context_hydrates_canonical_evidence_context():
    class FakePlans:
        def resolve(self, plan_id):
            from aipinho.services.context.context_plan_runtime_service import (
                ContextPlanResolution,
            )

            assert plan_id == "context_plan_child"
            return ContextPlanResolution(
                status="ready",
                source="context_kernel",
                plan={"plan_id": plan_id},
                bundle={"bundle_id": "bundle_child"},
                evidence_context=[
                    {
                        "artifact_id": "artifact_diag",
                        "logical_path": "diagnosis.md",
                        "content": "bounded diagnosis",
                    }
                ],
            )

        def status(self):
            return {"status": "ok"}

    run = runtime_run().model_copy(
        update={"context_injection_plan_id": "context_plan_child"}
    )

    context = TaskRunContextService(context_plans=FakePlans()).build(run)

    assert context.outputs["context_injection_plan"]["plan_id"] == "context_plan_child"
    assert context.outputs["context_bundle"]["bundle_id"] == "bundle_child"
    assert context.outputs["evidence_context"][0]["content"] == "bounded diagnosis"


def test_mission_context_handoff_materializes_artifact_through_kernel():
    class FakeArtifacts:
        def get(self, artifact_id):
            assert artifact_id == "artifact_diag"
            return ArtifactRecordV2(
                artifact_id=artifact_id,
                filename="diagnosis.md",
                display_name="Diagnosis",
                content_type="text/markdown",
                status="ready",
                artifact_type="markdown_report",
                session_id="session_test",
                run_id="task_run_parent",
                context_usable=True,
            )

        def use_as_context(self, request):
            assert request.sanitization_required is True
            return ArtifactContextUseResult(
                artifact_id=request.artifact_id,
                status="allowed",
                use_mode="attach_as_context",
                context_preview="Observed decoder failure with bounded evidence.",
                reason_code="artifact_context_use_allowed",
                evidence_refs=["evidence:decoder"],
            )

    class FakeKernel:
        def __init__(self):
            self.request = None

        def build(self, request):
            self.request = request
            bundle = ContextBundle(
                request_id=request.request_id,
                purpose=request.purpose,
                scope=request.scope,
                safe_for_prompt=True,
            )
            return SimpleNamespace(status="ok", bundle=bundle)

        def injection_plan(self, bundle_id, role_id=None):
            return ContextInjectionPlan(
                plan_id="context_plan_child",
                bundle_id=bundle_id,
                role_id=role_id,
                purpose="patch_planning",
                safe_for_prompt_assembly=True,
            )

    class FakePlans:
        def __init__(self):
            self.persisted = None

        def persist(self, plan):
            self.persisted = plan
            return plan

    kernel = FakeKernel()
    plans = FakePlans()
    service = MissionContextHandoffService(
        artifacts=FakeArtifacts(),
        kernel=kernel,
        plans=plans,
    )
    outcome = PhaseOutcome(
        producer_task_run_id="task_run_parent",
        producer_operation_id="operation_parent",
        session_id="session_test",
        phase_id="analysis",
        runtime_status="completed",
        result_status="completed",
        artifact_refs=["artifact_diag"],
        evidence_refs=["artifact_diag"],
        result_ref="task_run_result:task_run_parent",
        authority_sha256="f" * 64,
    )

    result = service.materialize(
        outcome=outcome,
        purpose="patch_planning",
        child_task_id="task_child",
        child_workspace_id="workspace_child",
    )

    assert result.status == "ready"
    assert result.plan_id == "context_plan_child"
    assert result.admitted_artifacts == ["artifact_diag"]
    assert plans.persisted is not None
    assert kernel.request is not None
    candidate = kernel.request.candidates[0]
    assert candidate.content == "Observed decoder failure with bounded evidence."
    assert candidate.source_ref.source_id == "artifact_diag"
    assert candidate.source_ref.path == "diagnosis.md"


def test_context_plan_runtime_resolves_canonical_inline_payload(tmp_path):
    bundle = ContextBundle(
        bundle_id="bundle_inline",
        request_id="request_inline",
        purpose="patch_planning",
        scope=ContextScope(session_id="session_inline"),
        safe_for_prompt=True,
    )
    plan = ContextInjectionPlan(
        plan_id="context_plan_inline",
        bundle_id=bundle.bundle_id,
        purpose="patch_planning",
        safe_for_prompt_assembly=True,
    )
    service = ContextPlanRuntimeService(
        store=CanonicalContextPlanStore(root=tmp_path / "plans_inline"),
        bundles=_BundleRepo(bundle),
        legacy_planner=_NoLegacyPlanner(),
        legacy_validator=_NoLegacyValidator(),
    )

    resolved = service.resolve_payload(plan.model_dump(mode="json"))

    assert resolved.status == "ready"
    assert resolved.source == "context_kernel"
    assert resolved.plan["plan_id"] == plan.plan_id
    assert resolved.bundle["bundle_id"] == bundle.bundle_id


def test_prompt_assembly_renders_canonical_context_without_rag_schema(tmp_path):
    source = ContextSourceRef(
        source_type="artifact_record",
        source_id="artifact_prompt",
        path="reports/diagnosis.md",
    )
    bundle = ContextBundle(
        bundle_id="bundle_prompt",
        request_id="request_prompt",
        purpose="patch_planning",
        scope=ContextScope(session_id="session_prompt"),
        items=[
            ContextItem(
                layer="attachments_artifacts",
                source_type="artifact_record",
                source_ref=source,
                summary="Diagnosis",
                content="Observed behavior: decoder selection loses prior diagnosis.",
                content_hash="b" * 64,
                citations=[
                    __import__(
                        "aipinho.schemas.context.contracts",
                        fromlist=["ContextCitation"],
                    ).ContextCitation(
                        citation_id="citation_prompt",
                        source_ref=source,
                        label="Diagnosis",
                    )
                ],
                trust_level="cited",
                budget_chars=58,
            )
        ],
        safe_for_prompt=True,
    )
    plan = ContextInjectionPlan(
        plan_id="context_plan_prompt",
        bundle_id=bundle.bundle_id,
        purpose="patch_planning",
        safe_for_prompt_assembly=True,
        citation_map=bundle.citation_map,
    )
    service = ContextPlanRuntimeService(
        store=CanonicalContextPlanStore(root=tmp_path / "plans_prompt"),
        bundles=_BundleRepo(bundle),
        legacy_planner=_NoLegacyPlanner(),
        legacy_validator=_NoLegacyValidator(),
    )

    assembly = PromptAssemblyService(context_plans=service).assemble(
        PromptAssemblyRequest(
            purpose="code_analysis",
            role_id="coder",
            user_message="Prepare a bounded proposal.",
            context_injection_plan=plan.model_dump(mode="json"),
        )
    )

    governed = [item for item in assembly.context_items if item.title == "Governed Context"]
    assert governed
    assert "citation_prompt" in str(assembly.messages)
    assert "decoder selection loses prior diagnosis" in str(assembly.messages)


def test_role_pipeline_uses_canonical_context_resolver_for_validation():
    class FakeContextPlans:
        def resolve_payload(self, payload):
            assert payload["plan_id"] == "context_plan_role"
            return ContextPlanResolution(
                status="ready",
                source="context_kernel",
                plan=payload,
                bundle={
                    "items": [
                        {
                            "layer": "attachments_artifacts",
                            "source_type": "artifact_record",
                        }
                    ]
                },
            )

        def resolve(self, plan_id):
            raise AssertionError(f"unexpected id resolution: {plan_id}")

    service = RolePipelineService(context_plans=FakeContextPlans())
    warnings = service._context_plan_warnings(
        RolePipelineRunRequest(
            context_injection_plan={
                "plan_id": "context_plan_role",
                "bundle_id": "bundle_role",
                "purpose": "patch_planning",
                "safe_for_prompt_assembly": True,
            }
        )
    )

    assert warnings == []
