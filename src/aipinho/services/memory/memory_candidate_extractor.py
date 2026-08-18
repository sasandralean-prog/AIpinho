from __future__ import annotations

from typing import Any

from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateRequest, MemoryCandidateScope, MemoryCandidateSource
from aipinho.services.memory.memory_candidate_source_resolver import MemoryCandidateSourceResolver


class MemoryCandidateExtractor:
    MAX_CANDIDATES = 20

    def __init__(self, resolver: MemoryCandidateSourceResolver | None = None) -> None:
        self.resolver = resolver or MemoryCandidateSourceResolver()

    def extract(self, *, source_type: str, source_id: str | None = None, payload: dict[str, Any] | None = None) -> tuple[MemoryCandidateSource, list[MemoryCandidateRequest]]:
        payload = payload or {}
        source = MemoryCandidateSource(source_type=source_type, source_id=source_id, source_ref=source_id or source_type, source_payload={}, trusted=source_type in MemoryCandidateSourceResolver.TRUSTED_SOURCES)
        if source_id and not payload:
            source, resolved_payload = self._resolve_by_id(source_type, source_id)
            payload = resolved_payload or {}
        requests = self._requests_for_source(source, payload)
        return source, requests[: self.MAX_CANDIDATES]

    def _resolve_by_id(self, source_type: str, source_id: str) -> tuple[MemoryCandidateSource, dict[str, Any] | None]:
        if source_type == "project_report":
            return self.resolver.from_project_report(source_id)
        if source_type == "task_run_result":
            return self.resolver.from_task_run(source_id)
        if source_type == "validation_result":
            return self.resolver.from_validation(source_id)
        if source_type == "patch_apply_result":
            return self.resolver.from_patch_apply(source_id)
        return MemoryCandidateSource(source_type=source_type, source_id=source_id, source_ref=source_id, trusted=False), None

    def _requests_for_source(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        if not payload:
            return [MemoryCandidateRequest(text=f"Source {source.source_type}:{source.source_id or 'unknown'} unavailable for extraction.", kind="known_limitation", source=source, scope=MemoryCandidateScope(scope_type="runtime"), evidence=[])]
        if source.source_type == "project_report":
            return self._from_report(source, payload)
        if source.source_type == "task_run_result":
            return self._from_task_result(source, payload)
        if source.source_type == "validation_result":
            return self._from_validation(source, payload)
        if source.source_type == "patch_apply_result":
            return self._from_patch_apply(source, payload)
        return self._from_manual_payload(source, payload)

    def _from_report(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        requests: list[MemoryCandidateRequest] = []
        workspace = payload.get("workspace")
        scope = MemoryCandidateScope(scope_type="workspace", workspace=workspace, reason="project_report")
        for index, finding in enumerate(payload.get("findings", []) or []):
            summary = str(finding.get("summary") or finding.get("title") or finding.get("description") or "")[:500]
            if summary:
                requests.append(self._request(summary, "architecture_decision", source, scope, f"report_finding_{index}", "report_finding"))
        for index, recommendation in enumerate(payload.get("recommendations", []) or []):
            summary = str(recommendation.get("summary") or recommendation.get("description") or recommendation)[:500]
            if summary:
                requests.append(self._request(summary, "operational_procedure", source, scope, f"report_recommendation_{index}", "report_finding"))
        for index, limitation in enumerate(payload.get("limitations", []) or []):
            requests.append(self._request(str(limitation), "known_limitation", source, scope, f"report_limitation_{index}", "report_finding"))
        return requests

    def _from_task_result(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        scope = MemoryCandidateScope(scope_type="runtime", reason="task_run_result")
        requests = []
        if payload.get("summary"):
            requests.append(self._request(str(payload["summary"]), "runtime_behavior", source, scope, "task_result_summary", "task_result"))
        for index, limitation in enumerate(payload.get("limitations", []) or []):
            requests.append(self._request(str(limitation), "known_limitation", source, scope, f"task_limitation_{index}", "task_result"))
        for index, blocked in enumerate(payload.get("blocked_items", []) or []):
            requests.append(self._request(str(blocked), "risk_pattern", source, scope, f"task_blocked_{index}", "task_result"))
        return requests

    def _from_validation(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        scope = MemoryCandidateScope(scope_type="validation", reason="validation_result")
        requests = []
        for index, finding in enumerate(payload.get("findings", []) or []):
            summary = str(finding.get("message") or finding.get("summary") or finding)[:500]
            requests.append(self._request(summary, "validation_learning", source, scope, f"validation_finding_{index}", "validation_finding"))
        for index, warning in enumerate(payload.get("warnings", []) or []):
            requests.append(self._request(str(warning), "risk_pattern", source, scope, f"validation_warning_{index}", "validation_finding"))
        if not requests and payload.get("status"):
            requests.append(self._request(f"Validation result status: {payload.get('status')}", "validation_learning", source, scope, "validation_status", "validation_finding"))
        return requests

    def _from_patch_apply(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        scope = MemoryCandidateScope(scope_type="patching", reason="patch_apply_result")
        status = payload.get("status", "unknown")
        text = f"Patch apply result {source.source_id or ''} finished with status {status}; post validation passed={payload.get('post_apply_validation', {}).get('passed', False)}."
        if status in {"rollback_failed", "failed"}:
            kind = "risk_pattern"
        else:
            kind = "patch_outcome"
        return [self._request(text, kind, source, scope, "patch_apply_result", "patch_apply_result")]

    def _from_manual_payload(self, source: MemoryCandidateSource, payload: dict[str, Any]) -> list[MemoryCandidateRequest]:
        text = str(payload.get("text") or payload.get("summary") or "")
        scope_type = str(payload.get("scope_type") or "")
        scope = MemoryCandidateScope(scope_type=scope_type, workspace=payload.get("workspace"), reason="manual_payload")
        return [MemoryCandidateRequest(text=text, kind=payload.get("kind"), source=source, scope=scope, metadata={"manual_payload": True})]

    def _request(self, text: str, kind: str, source: MemoryCandidateSource, scope: MemoryCandidateScope, evidence_id: str, evidence_type: str) -> MemoryCandidateRequest:
        evidence = [MemoryCandidateEvidence(evidence_id=evidence_id, evidence_type=evidence_type, source_ref=source.source_ref or source.source_type, summary=text[:300])]
        return MemoryCandidateRequest(text=text, kind=kind, source=source, scope=scope, evidence=evidence)
