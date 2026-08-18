from __future__ import annotations

from aipinho.schemas.reports.project_report import ProjectReport


class ReportFormatter:
    def to_markdown(self, report: ProjectReport, *, max_chars: int | None = None) -> str:
        lines: list[str] = []
        lines.append(f"# Project Report - {report.goal}")
        lines.append("")
        lines.append(f"Generated at: {report.generated_at}")
        lines.append(f"Workspace: `{report.workspace}`")
        lines.append(f"Status: `{report.status}`")
        lines.append("")
        lines.append("> Read-only report: no files were written, no patch was applied, no shell/git/memory/RAG/LLM execution was required.")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append(report.executive_summary)
        lines.append("")
        for section in report.sections:
            if section.section_id in {"executive_summary", "findings", "limitations"}:
                continue
            if not section.content and not section.items:
                continue
            lines.append(f"## {section.title}")
            if section.content:
                lines.append(section.content)
            for item in section.items:
                title = str(item.get("title") or item.get("structure") or item.get("category") or "Item")
                summary = str(item.get("summary") or "").strip()
                evidence_paths = item.get("evidence_paths") or []
                if summary:
                    lines.append(f"- **{title}:** {summary}")
                else:
                    lines.append(f"- {title}")
                if isinstance(evidence_paths, list) and evidence_paths:
                    lines.append(f"  - Evidencia: {', '.join(str(path) for path in evidence_paths[:6])}")
                details = item.get("details")
                if isinstance(details, dict):
                    for key, value in details.items():
                        if value is None or value == "" or value == () or value == []:
                            continue
                        if isinstance(value, list):
                            rendered = ", ".join(str(part) for part in value[:10])
                        else:
                            rendered = str(value)
                        lines.append(f"  - {key}: {rendered}")
            lines.append("")
        if report.findings:
            lines.append("## Evidence-Based Findings")
            lines.append("| Severity | Category | Title | Evidence |")
            lines.append("| --- | --- | --- | --- |")
            for finding in report.findings:
                refs = ", ".join((item.path or item.source_type) for item in finding.evidence[:3])
                lines.append(f"| {finding.severity} | {finding.category} | {finding.title} | {refs} |")
            lines.append("")
            for finding in report.findings:
                lines.append(f"### {finding.title}")
                lines.append(f"Severity: `{finding.severity}` - Confidence: `{finding.confidence:.2f}`")
                lines.append(f"Summary: {finding.summary}")
                lines.append(f"Inference: {finding.inference}")
                lines.append(f"Recommendation: {finding.recommendation}")
                lines.append("Evidence:")
                for evidence in finding.evidence:
                    location = evidence.path or evidence.source_type
                    line_part = f":{evidence.line_start}-{evidence.line_end}" if evidence.line_start and evidence.line_end else ""
                    lines.append(f"- `{location}{line_part}` ({evidence.source_type}, confidence {evidence.confidence:.2f})")
                    if evidence.excerpt:
                        excerpt = evidence.excerpt.replace("\n", " ")[:220]
                        lines.append(f"  - Excerpt: {excerpt}")
                lines.append("")
        if report.recommendations:
            lines.append("## Recommendations")
            for recommendation in report.recommendations:
                lines.append(f"- {recommendation.summary}")
            lines.append("")
        lines.append("## Limitations")
        if report.limitations:
            for limitation in report.limitations:
                lines.append(f"- {limitation}")
        else:
            lines.append("- No blocking limitation recorded.")
        lines.append("")
        lines.append("## Trace Summary")
        for trace in report.trace:
            lines.append(f"- {trace.stage}: {trace.status} ({trace.reason})")
        if report.requested_deliverables:
            lines.append("")
            lines.append("## Deliverable Contract")
            lines.append(
                "- Requested: " + ", ".join(report.requested_deliverables)
            )
            lines.append(
                "- Fulfilled: " + ", ".join(report.fulfilled_deliverables)
            )
            if report.missing_deliverables:
                lines.append(
                    "- Missing: " + ", ".join(report.missing_deliverables)
                )
        markdown = "\n".join(lines).strip() + "\n"
        if max_chars and len(markdown) > max_chars:
            return markdown[:max_chars] + "\n\n[report_truncated_by_response_limit]\n"
        return markdown

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "report_formatter"}
