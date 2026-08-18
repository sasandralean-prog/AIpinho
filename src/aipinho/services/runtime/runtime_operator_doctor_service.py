from __future__ import annotations

import csv
import io
from typing import Any

from aipinho.schemas.runtime.runtime_operator import (
    DoctorEvidence,
    DoctorRecommendation,
    DoctorSummary,
    ExpectedRuntimeContract,
    FireTestDoctorResult,
    RegressionCategory,
    RegressionFinding,
    RegressionMatrix,
    RegressionMatrixRow,
    RuntimeDoctorReport,
    RuntimeExplanation,
    RuntimePatchPlan,
    RuntimeSnapshot,
    PatchPlanItem,
)
from aipinho.services.runtime.runtime_operator_service import RuntimeOperatorService


CATEGORY_TO_SNAPSHOT_FIELD: dict[RegressionCategory, str] = {
    "Intent": "current_intent",
    "Lifecycle": "current_lifecycle",
    "Workspace": "current_workspace",
    "Artifacts": "current_artifacts",
    "Approval": "approval",
    "Validation": "current_validation",
    "Completion": "current_completion",
    "SpeakerTruth": "current_speaker_truth",
    "Dispatcher": "dispatcher",
    "SemanticIR": "semantic_ir",
    "ExecutionPlan": "execution_plan",
    "Contracts": "current_contracts",
    "RoleSelection": "current_roles",
    "Timeline": "timeline",
    "Executor": "executor",
    "Models": "models",
    "Tools": "tools",
    "Skills": "skills",
}

CATEGORY_TO_EXPECTED_FIELD: dict[RegressionCategory, str] = {
    "Intent": "intent",
    "Lifecycle": "lifecycle",
    "Workspace": "workspace",
    "Artifacts": "artifacts",
    "Approval": "approval",
    "Validation": "validation",
    "Completion": "completion",
    "SpeakerTruth": "speaker_truth",
    "Dispatcher": "dispatcher",
    "Timeline": "timeline",
    "SemanticIR": "semantic_ir",
    "ExecutionPlan": "execution_plan",
    "Contracts": "contracts",
    "RoleSelection": "roles",
    "Executor": "executor",
    "Models": "models",
    "Tools": "tools",
    "Skills": "skills",
}

SUSPECTED_MODULES: dict[RegressionCategory, list[str]] = {
    "Intent": ["services/semantic_runtime", "services/chat", "services/runtime/runtime_dispatcher_v2_service.py"],
    "Lifecycle": ["services/runtime/task_run_lifecycle_service.py", "services/runtime/canonical_operation_state_service.py"],
    "Workspace": ["services/runtime/workspace_context_service.py", "services/workspaces"],
    "Artifacts": ["services/artifacts", "services/runtime/canonical_operation_state_service.py"],
    "Approval": ["services/approvals", "services/chat/chat_approval_command_service.py"],
    "Validation": ["services/validation", "services/runtime/task_run_guard.py"],
    "Completion": ["services/runtime/task_completion.py", "services/runtime/canonical_operation_state_service.py"],
    "SpeakerTruth": ["services/runtime/runtime_truth_engine.py", "services/speaker"],
    "Dispatcher": ["services/runtime/runtime_dispatcher_v2_service.py"],
    "Timeline": ["services/runtime/runtime_timeline_service.py"],
    "SemanticIR": ["services/semantic_runtime"],
    "ExecutionPlan": ["services/runtime/planner_v2_service.py"],
    "Contracts": ["services/runtime/runtime_contracts_v2_service.py", "schemas/runtime/runtime_contracts_v2.py"],
    "RoleSelection": ["services/roles/role_contract_service.py", "services/runtime/runtime_dispatcher_v2_service.py"],
    "Executor": ["services/runtime/task_run_executor.py", "services/runtime/supervised_execution_loop.py"],
    "Models": ["services/models", "services/semantic_runtime/capability_registry.py"],
    "Tools": ["services/tools", "services/runtime/tool_governance_service.py"],
    "Skills": ["services/skills", "services/runtime/skill_runtime_service.py"],
}


class RuntimeOperatorDoctorService:
    def analyze(self, snapshot: RuntimeSnapshot, expected: ExpectedRuntimeContract) -> RuntimeDoctorReport:
        rows: list[RegressionMatrixRow] = []
        findings: list[RegressionFinding] = []
        evidence: list[DoctorEvidence] = []
        recommendations: list[DoctorRecommendation] = []
        for category, snapshot_field in CATEGORY_TO_SNAPSHOT_FIELD.items():
            expected_field = CATEGORY_TO_EXPECTED_FIELD[category]
            expected_value = getattr(expected, expected_field)
            observation = getattr(snapshot, snapshot_field)
            if expected_value is None:
                rows.append(RegressionMatrixRow(category=category, status="NOT_APPLICABLE"))
                continue
            actual_value = observation.value
            evidence.append(
                DoctorEvidence(
                    domain=category,
                    source=observation.source or snapshot_field,
                    observed=actual_value,
                    expected=expected_value,
                    refs=[snapshot.snapshot_id],
                )
            )
            if self._matches_expected(actual_value, expected_value):
                rows.append(RegressionMatrixRow(category=category, status="PASS"))
                continue
            if observation.status == "unavailable":
                reason_code = f"{category.lower()}_unavailable"
                rows.append(RegressionMatrixRow(category=category, status="WARN", severity="medium", reason_code=reason_code))
                recommendations.append(
                    DoctorRecommendation(
                        domain=category,
                        priority="medium",
                        action="Restore observability for this runtime domain before treating it as a contract regression.",
                        rationale=f"{category} was expected but the observation source is unavailable.",
                    )
                )
                continue
            severity = "high" if category in {"Intent", "Lifecycle", "Completion", "SpeakerTruth"} else "medium"
            reason_code = f"{category.lower()}_regression"
            rows.append(RegressionMatrixRow(category=category, status="FAIL", severity=severity, reason_code=reason_code))
            findings.append(
                RegressionFinding(
                    category=category,
                    severity=severity,
                    expected=expected_value,
                    actual=actual_value,
                    reason_code=reason_code,
                    summary=f"{category} expected {self._short(expected_value)} but observed {self._short(actual_value)}.",
                    evidence_refs=[snapshot.snapshot_id, observation.source or snapshot_field],
                    suspected_modules=SUSPECTED_MODULES[category],
                )
            )
            recommendations.append(
                DoctorRecommendation(
                    domain=category,
                    priority=severity,
                    action="Investigate the suspected modules and add a focused regression test before patching.",
                    rationale=f"{category} did not match the expected contract.",
                )
            )
        summary = self._summary(rows)
        report = RuntimeDoctorReport(
            snapshot_id=snapshot.snapshot_id,
            status="regressions_found" if findings else "passed",
            summary=summary,
            matrix=RegressionMatrix(rows=rows),
            findings=findings,
            evidence=evidence,
            recommendations=recommendations,
            deterministic=True,
            read_only=True,
            side_effects=False,
        )
        report.markdown = self.to_markdown(report)
        report.csv = self.to_csv(report)
        return report

    def to_markdown(self, report: RuntimeDoctorReport) -> str:
        lines = [
            f"# Runtime Doctor Report {report.report_id}",
            "",
            f"- snapshot_id: {report.snapshot_id}",
            f"- status: {report.status}",
            f"- summary_status: {report.summary.status}",
            f"- findings: {len(report.findings)}",
            f"- generated_artifacts: {', '.join(report.metadata.generated_artifacts)}",
            "",
            "## Regression Matrix",
            "",
            "| Category | Status | Severity | Reason |",
            "| --- | --- | --- | --- |",
        ]
        for row in report.matrix.rows:
            lines.append(f"| {row.category} | {row.status} | {row.severity} | {row.reason_code or ''} |")
        if report.findings:
            lines.extend(["", "## Findings", ""])
            for finding in report.findings:
                lines.append(f"- **{finding.category}** `{finding.reason_code}`: {finding.summary}")
        if report.recommendations:
            lines.extend(["", "## Recommendations", ""])
            for recommendation in report.recommendations:
                lines.append(f"- **{recommendation.domain}** `{recommendation.priority}`: {recommendation.action}")
        return "\n".join(lines)

    def to_csv(self, report: RuntimeDoctorReport) -> str:
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=["category", "status", "severity", "reason_code"])
        writer.writeheader()
        for row in report.matrix.rows:
            writer.writerow({"category": row.category, "status": row.status, "severity": row.severity, "reason_code": row.reason_code or ""})
        return stream.getvalue()

    def _short(self, value: Any) -> str:
        text = repr(value)
        return text if len(text) <= 120 else f"{text[:117]}..."

    def _matches_expected(self, actual: Any, expected: Any) -> bool:
        if expected is None:
            return True
        if actual == expected:
            return True
        if isinstance(expected, dict):
            if isinstance(actual, list):
                return self._matches_list_summary(actual, expected)
            if not isinstance(actual, dict):
                return False
            for key, expected_value in expected.items():
                if key == "required" and key not in actual:
                    if expected_value is True:
                        if actual:
                            continue
                        return False
                    if expected_value is False:
                        if not actual:
                            continue
                        return False
                if key not in actual:
                    return False
                if not self._matches_expected(actual.get(key), expected_value):
                    return False
            return True
        if isinstance(expected, list):
            if not isinstance(actual, list):
                return False
            unmatched = list(actual)
            for expected_item in expected:
                match_index = next(
                    (
                        index
                        for index, actual_item in enumerate(unmatched)
                        if self._matches_expected(actual_item, expected_item)
                    ),
                    None,
                )
                if match_index is None:
                    return False
                unmatched.pop(match_index)
            return True
        return False

    def _matches_list_summary(self, actual: list[Any], expected: dict[str, Any]) -> bool:
        supported_keys = {"count", "required", "items"}
        if any(key not in supported_keys for key in expected):
            return False
        if "count" in expected and len(actual) != expected["count"]:
            return False
        if "required" in expected:
            observed_refs = set()
            for item in actual:
                if isinstance(item, dict):
                    for key in ("logical_path", "label", "artifact_id", "id"):
                        if item.get(key) is not None:
                            observed_refs.add(str(item[key]))
                elif item is not None:
                    observed_refs.add(str(item))
            for required in expected["required"] or []:
                if str(required) not in observed_refs:
                    return False
        if "items" in expected and not self._matches_expected(actual, expected["items"]):
            return False
        return True

    def _summary(self, rows: list[RegressionMatrixRow]) -> DoctorSummary:
        counts = {status: sum(1 for row in rows if row.status == status) for status in ("PASS", "WARN", "FAIL", "NOT_APPLICABLE")}
        status = "FAIL" if counts["FAIL"] else "WARN" if counts["WARN"] else "PASS"
        severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        highest = max((row.severity for row in rows), key=lambda item: severity_order.get(item, 0), default="info")
        return DoctorSummary(
            status=status,
            pass_count=counts["PASS"],
            warn_count=counts["WARN"],
            fail_count=counts["FAIL"],
            not_applicable_count=counts["NOT_APPLICABLE"],
            highest_severity=highest,
        )


class RuntimeExplainerService:
    def explain(self, report: RuntimeDoctorReport, snapshot: RuntimeSnapshot | None = None) -> RuntimeExplanation:
        if report.status == "passed":
            summary = "Runtime Doctor did not find contract regressions in the supplied snapshot."
        else:
            summary = f"Runtime Doctor found {len(report.findings)} contract regression(s) that require engineering review."
        return RuntimeExplanation(
            report_id=report.report_id,
            executive_summary=summary,
            regressions=[finding.summary for finding in report.findings],
            impact=[f"{finding.category}: may make runtime state inconsistent for clients." for finding in report.findings],
            hypotheses=[f"Inspect {', '.join(finding.suspected_modules)} for {finding.reason_code}." for finding in report.findings],
            risks=["Explanation is advisory only; it does not approve, execute, patch, or change runtime state."],
            decision_made=False,
            patch_generated=False,
            read_only=True,
            side_effects=False,
        )


class RuntimePatchPlannerService:
    def plan(self, report: RuntimeDoctorReport, *, source_hints: list[str] | None = None) -> RuntimePatchPlan:
        if not report.findings:
            return RuntimePatchPlan(
                report_id=report.report_id,
                status="no_patch_needed",
                confidence=1.0,
                risk="info",
                applies_patch=False,
                read_only=True,
                side_effects=False,
            )
        modules = list(dict.fromkeys([module for finding in report.findings for module in finding.suspected_modules] + list(source_hints or [])))
        items = [
            PatchPlanItem(
                module=module,
                reason="Module is implicated by at least one Runtime Doctor regression finding.",
                risk="medium",
                proposed_action="Inspect the module, add a focused regression test, then patch only the canonical contract path if the bug is reproduced.",
                rollback="Revert only the focused patch and preserve the Runtime Doctor report as evidence.",
                tests=["tests/unit/test_runtime_operator_ro.py", "targeted regression for affected module"],
            )
            for module in modules
        ]
        return RuntimePatchPlan(
            report_id=report.report_id,
            status="planned",
            confidence=0.72,
            risk="medium",
            affected_modules=modules,
            items=items,
            tests=list(dict.fromkeys([test for item in items for test in item.tests])),
            rollback=list(dict.fromkeys([item.rollback for item in items])),
            applies_patch=False,
            read_only=True,
            side_effects=False,
        )


class FireTestDoctorService:
    def analyze(self, raw: dict[str, Any], expected: ExpectedRuntimeContract, *, source_hints: list[str] | None = None) -> FireTestDoctorResult:
        snapshot = RuntimeOperatorService().snapshot(runtime_data=self._runtime_data_from_raw(raw))
        report = RuntimeOperatorDoctorService().analyze(snapshot, expected)
        plan = RuntimePatchPlannerService().plan(report, source_hints=source_hints)
        return FireTestDoctorResult(
            doctor_report=report,
            regression_matrix=report.matrix,
            patch_plan=plan,
            read_only=True,
            side_effects=False,
        )

    def _runtime_data_from_raw(self, raw: dict[str, Any]) -> dict[str, Any]:
        if "runtime_data" in raw and isinstance(raw["runtime_data"], dict):
            return dict(raw["runtime_data"])
        data = dict(raw)
        session = raw.get("universal_task_session")
        if isinstance(session, dict):
            data.setdefault("task_id", session.get("task_id"))
            data.setdefault("task_run_id", session.get("task_run_id"))
            data.setdefault("status", session.get("status"))
            data.setdefault("phase", session.get("phase"))
        return data
