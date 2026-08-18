from types import SimpleNamespace

from tests.support.runtime_fixtures import runtime_context, runtime_run

from aipinho.schemas.reports.report_request import ProjectReportRequest
from aipinho.services.orchestration.task_completion_resolver import TaskCompletionResolver
from aipinho.services.prompt_intelligence.prompt_intelligence_service import (
    PromptIntelligenceService,
)
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.prompt_intelligence.report_deliverable_extractor_service import (
    ReportDeliverableExtractorService,
)
from aipinho.services.reports.project_report_service import ProjectReportService


def test_report_deliverable_extractor_reads_explicit_bullets():
    prompt = """
    Gere:
    * diagnostico inicial;
    * plano macro em sprints;
    * proposta do Sprint 1;
    * evidencias usadas.
    """

    deliverables = ReportDeliverableExtractorService().extract(prompt)

    assert "initial_diagnosis" in deliverables
    assert "macro_plan" in deliverables
    assert "first_sprint" in deliverables
    assert "evidence" in deliverables


def test_prompt_intelligence_preserves_workspace_references_and_deliverables(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    prompt = f"""
    Fonte legada read-only:
    {source}

    Workspace alvo mutavel:
    {target}

    Faca apenas analise read-only agora.
    Gere:
    * plano macro em sprints;
    * proposta do Sprint 1;
    * estado atual do workspace alvo.
    """

    intent_map = PromptIntelligenceService().analyze(
        PromptAnalysisRequest(prompt=prompt)
    ).intent_map

    roles = {item.role for item in intent_map.workspace_references}
    assert "source_readonly" in roles
    assert "target_mutable" in roles
    assert "macro_plan" in intent_map.requested_deliverables
    assert "first_sprint" in intent_map.requested_deliverables
    assert "target_workspace_status" in intent_map.requested_deliverables


def test_project_report_fulfills_requested_plan_sections(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "README.md").write_text("# Demo\n\nDesktop project.\n", encoding="utf-8")
    (source / "build.gradle.kts").write_text("plugins { kotlin(\"jvm\") }\n", encoding="utf-8")
    (source / "src").mkdir()
    (source / "src" / "Main.kt").write_text("fun main() = println(\"ok\")\n", encoding="utf-8")

    response = ProjectReportService().generate_report(
        ProjectReportRequest(
            workspace=str(source),
            requested_deliverables=[
                "target_workspace_status",
                "macro_plan",
                "first_sprint",
                "risks",
                "permissions",
                "next_steps",
                "evidence",
            ],
            workspace_references=[
                {"path": str(source), "role": "source_readonly", "confidence": 0.95},
                {"path": str(target), "role": "target_mutable", "confidence": 0.95},
            ],
        )
    )

    assert response.report is not None
    assert response.report.missing_deliverables == []
    assert "target_workspace_status" in response.report.fulfilled_deliverables
    assert "macro_plan" in response.report.fulfilled_deliverables
    assert "first_sprint" in response.report.fulfilled_deliverables
    assert response.rendered_markdown is not None
    assert "Target Workspace Status" in response.rendered_markdown
    assert "Macro Portability and Correction Plan" in response.rendered_markdown
    assert "Proposed First Sprint" in response.rendered_markdown


def test_completion_resolver_marks_missing_requested_deliverable_partial():
    run = runtime_run()
    run.contract_type = "readonly_analysis"
    run.intent_map = {"requested_deliverables": ["macro_plan"]}
    context = runtime_context(run)
    context.outputs["_project_analysis"] = {"status": "ok"}
    context.outputs["_project_report"] = SimpleNamespace(
        report=SimpleNamespace(
            report_id="project_report_test",
            fulfilled_deliverables=[],
            missing_deliverables=["macro_plan"],
        )
    )

    evaluation = TaskCompletionResolver().resolve(run, context, proposed_status="completed")

    assert evaluation.status == "partial"
    assert evaluation.safe_to_report_success is False
    assert "deliverable:macro_plan" in evaluation.missing_outcomes


def test_completion_resolver_allows_success_when_required_evidence_exists():
    run = runtime_run()
    run.contract_type = "readonly_analysis"
    run.intent_map = {"requested_deliverables": ["macro_plan"]}
    context = runtime_context(run)
    context.outputs["_project_analysis"] = {"status": "ok"}
    context.outputs["_project_report"] = SimpleNamespace(
        report=SimpleNamespace(
            report_id="project_report_test",
            fulfilled_deliverables=["macro_plan"],
            missing_deliverables=[],
        )
    )

    evaluation = TaskCompletionResolver().resolve(run, context, proposed_status="completed")

    assert evaluation.status == "completed"
    assert evaluation.safe_to_report_success is True
    assert "deliverable:macro_plan" in evaluation.fulfilled_outcomes
