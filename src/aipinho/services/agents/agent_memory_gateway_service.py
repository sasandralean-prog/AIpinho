from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunUpdateRequest
from aipinho.schemas.agents.memory import (
    MemoryAccessLog,
    MemoryCandidate,
    MemoryCandidateCreateRequest,
    MemoryCandidateReviewRequest,
    MemoryContextLoadRequest,
    MemoryContextLoadResult,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemorySupersedeRequest,
    MemoryWriteRequest,
    MemoryWriteResult,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_memory_gateway_store import AgentMemoryGatewayStore
from aipinho.services.agents.agent_memory_policy_service import AgentMemoryPolicyService, PRIVATE_NAMESPACE_BY_AGENT
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.events.event_core import redact_payload


class AgentMemoryGatewayService:
    def __init__(
        self,
        *,
        store: AgentMemoryGatewayStore | None = None,
        policy: AgentMemoryPolicyService | None = None,
        kernel: AgentSessionKernelService | None = None,
    ) -> None:
        self.store = store or AgentMemoryGatewayStore()
        self.policy = policy or AgentMemoryPolicyService()
        self.kernel = kernel or AgentSessionKernelService()
        self.store.ensure_namespaces(self.policy.namespaces())

    def namespaces(self):
        return self.store.ensure_namespaces(self.policy.namespaces())

    def status(self) -> dict[str, Any]:
        records = self.store.list_records(include_all=True)
        candidates = self.store.list_candidates(include_all=True)
        return {
            "status": "ok",
            "mode": "multi_agent_memory_gateway",
            "namespaces": len(self.namespaces()),
            "records": len(records),
            "candidates": len(candidates),
            "shared_memory_governed": True,
            "raw_hidden_by_default": True,
            "secret_storage_blocked": True,
        }

    def write_memory(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        scope = request.scope or self._scope_for_namespace(str(request.namespace))
        request = request.model_copy(update={"scope": scope})
        policy = self.policy.evaluate_write(request)
        if policy.decision != "deny":
            request = request.model_copy(update={"content_sanitized": str(redact_payload(request.content_sanitized)), "metadata_sanitized": redact_payload(request.metadata_sanitized)})
            policy = self.policy.evaluate_write(request)
        warnings = list(policy.warnings)
        if policy.decision == "deny":
            self._access(None, None, request.agent_id, "write", policy.reason_code, request.session_id, request.run_id, {"namespace": request.namespace})
            self._event(request.run_id, "memory_access_denied", policy.human_reason, {"namespace": request.namespace, "reason_code": policy.reason_code}, severity="warning")
            return MemoryWriteResult(status="blocked", policy=policy, warnings=warnings)
        if policy.decision in {"candidate_only", "require_validation"}:
            candidate = self.create_candidate(
                MemoryCandidateCreateRequest(
                    proposed_by_agent_id=request.agent_id,
                    namespace=request.namespace,
                    scope=scope,
                    title=request.title,
                    content_sanitized=request.content_sanitized,
                    memory_type=request.memory_type,
                    source_ref=request.source_ref,
                    evidence_refs=request.evidence_refs,
                    confidence=request.confidence,
                    reason_to_remember=request.reason or policy.reason_code,
                    session_id=request.session_id,
                    run_id=request.run_id,
                    metadata_sanitized=request.metadata_sanitized,
                )
            )
            return MemoryWriteResult(status="candidate_created", candidate=candidate, policy=policy, warnings=[*warnings, policy.reason_code])
        record = MemoryRecord(
            namespace=request.namespace,
            agent_id=request.agent_id if scope == "private" else None,
            scope=scope,
            title=request.title[:240],
            content_sanitized=request.content_sanitized[: self._max_record_chars()],
            memory_type=request.memory_type,
            source_type=request.source_type,
            source_ref=request.source_ref,
            evidence_refs=request.evidence_refs,
            confidence=request.confidence,
            freshness=self._freshness_for(request.memory_type),
            validation_status=request.validation_status or ("validated" if request.namespace != "memory:shared" else "candidate"),
            tags=request.tags,
            project_id=request.project_id,
            workspace_id=request.workspace_id,
            supersedes=request.supersedes,
            metadata_sanitized=request.metadata_sanitized,
        )
        if request.supersedes:
            old = self.store.get_record(request.supersedes)
            if old is not None:
                old = self.store.save_record(old.model_copy(update={"validation_status": "superseded", "freshness": "stale", "superseded_by": record.memory_id}))
                record = record.model_copy(update={"evidence_refs": [*record.evidence_refs, f"memory:{old.memory_id}"]})
                self._event(request.run_id, "memory_superseded", "Memoria anterior marcada como superseded.", {"memory_id": old.memory_id, "superseded_by": record.memory_id})
        contradiction_refs = self._detect_contradictions(record)
        if contradiction_refs:
            record = record.model_copy(update={"validation_status": "contradicted", "contradiction_refs": contradiction_refs, "freshness": "stale"})
            self._event(request.run_id, "memory_contradiction_detected", "Possivel contradicao de memoria detectada.", {"memory_id": record.memory_id, "contradiction_refs": contradiction_refs}, severity="warning")
            warnings.append("contradicted_memory_detected")
        record = self.store.save_record(record)
        self._access(record.memory_id, None, request.agent_id, "write", policy.reason_code, request.session_id, request.run_id, {"namespace": request.namespace})
        self._event(request.run_id, "memory_written", "Memoria governada gravada.", {"memory_id": record.memory_id, "namespace": record.namespace, "validation_status": record.validation_status}, evidence_refs=[f"memory:{record.memory_id}"])
        self._update_run_memory_refs(request.run_id, written=[record.memory_id], warnings=warnings)
        return MemoryWriteResult(status="written", memory=record, policy=policy, warnings=warnings)

    def create_candidate(self, request: MemoryCandidateCreateRequest) -> MemoryCandidate:
        policy_probe = self.policy.evaluate_write(
            MemoryWriteRequest(
                agent_id=request.proposed_by_agent_id,
                namespace=request.namespace,
                scope=request.scope,
                title=request.title,
                content_sanitized=request.content_sanitized,
                memory_type=request.memory_type,
                source_ref=request.source_ref,
                evidence_refs=request.evidence_refs,
                confidence=request.confidence,
                metadata_sanitized=request.metadata_sanitized,
            )
        )
        if policy_probe.decision == "deny":
            raise PermissionError(policy_probe.reason_code)
        request = request.model_copy(update={"content_sanitized": str(redact_payload(request.content_sanitized)), "metadata_sanitized": redact_payload(request.metadata_sanitized)})
        scope = request.scope or self._scope_for_namespace(str(request.namespace))
        warnings = []
        if not request.evidence_refs and request.namespace in {"memory:shared", "memory:regression"}:
            warnings.append("missing_evidence_ref")
        candidate = MemoryCandidate(
            proposed_by_agent_id=request.proposed_by_agent_id,
            namespace=request.namespace,
            scope=scope,
            title=request.title[:240],
            content_sanitized=request.content_sanitized[: self._max_record_chars()],
            memory_type=request.memory_type,
            source_ref=request.source_ref,
            evidence_refs=request.evidence_refs,
            confidence=request.confidence,
            reason_to_remember=request.reason_to_remember,
            warnings=warnings,
            metadata_sanitized=request.metadata_sanitized,
        )
        candidate = self.store.save_candidate(candidate)
        self._access(None, candidate.candidate_id, request.proposed_by_agent_id, "write", "candidate_created", request.session_id, request.run_id, {"namespace": request.namespace})
        self._event(request.run_id, "memory_candidate_created", "Memory candidate criado.", {"candidate_id": candidate.candidate_id, "namespace": candidate.namespace, "warnings": warnings}, evidence_refs=[f"memory_candidate:{candidate.candidate_id}"])
        self._update_run_memory_refs(request.run_id, candidates=[candidate.candidate_id], warnings=warnings)
        return candidate

    def accept_candidate(self, candidate_id: str, request: MemoryCandidateReviewRequest) -> MemoryWriteResult:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        result = self.write_memory(
            MemoryWriteRequest(
                agent_id=request.agent_id,
                namespace=candidate.namespace,
                scope=candidate.scope,
                title=candidate.title,
                content_sanitized=candidate.content_sanitized,
                memory_type=candidate.memory_type,
                source_type="agent_summary",
                source_ref=candidate.source_ref,
                evidence_refs=candidate.evidence_refs,
                confidence=candidate.confidence,
                validation_status=request.validation_status,
                reason=request.reason or "candidate_accepted",
                session_id=None,
                run_id=None,
                metadata_sanitized={"candidate_id": candidate.candidate_id, "memory_review_accepted": True},
            )
        )
        if result.memory is not None:
            candidate = candidate.model_copy(update={"status": "accepted", "reviewed_by": request.reviewed_by or request.agent_id, "memory_id": result.memory.memory_id})
            self.store.save_candidate(candidate)
            self._access(result.memory.memory_id, candidate.candidate_id, request.agent_id, "validate", "candidate_accepted", None, None, {})
        return result

    def reject_candidate(self, candidate_id: str, request: MemoryCandidateReviewRequest) -> MemoryCandidate:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        candidate = self.store.save_candidate(candidate.model_copy(update={"status": "rejected", "reviewed_by": request.reviewed_by or request.agent_id}))
        self._access(None, candidate.candidate_id, request.agent_id, "reject", request.reason or "candidate_rejected", None, None, {})
        return candidate

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        namespaces = self.policy.allowed_namespaces_for_search(request)
        records: list[MemoryRecord] = []
        warnings: list[str] = []
        query = (request.query or "").lower().strip()
        tags = {tag.lower() for tag in request.tags}
        for namespace in namespaces:
            for record in self.store.list_records(namespace=namespace):
                allowed, record_warnings = self.policy.can_read_record(request.agent_id, record)
                if not allowed:
                    continue
                if request.memory_type and record.memory_type != request.memory_type:
                    continue
                if request.workspace_id and record.workspace_id != request.workspace_id:
                    continue
                if request.project_id and record.project_id != request.project_id:
                    continue
                if tags and not tags.intersection({tag.lower() for tag in record.tags}):
                    continue
                haystack = f"{record.title}\n{record.content_sanitized}\n{' '.join(record.tags)}".lower()
                if query:
                    terms = [term for term in query.split() if term]
                    if query not in haystack and not all(term in haystack for term in terms):
                        continue
                if not request.include_stale and (record.freshness == "stale" or record.validation_status in {"stale", "contradicted"}):
                    continue
                records.append(record)
                warnings.extend(record_warnings)
        records = records[: max(1, min(request.limit, 100))]
        access_logs = [self._access(record.memory_id, None, request.agent_id, "read", request.reason, request.session_id, request.run_id, {"namespace": record.namespace}) for record in records]
        candidates: list[MemoryCandidate] = []
        if request.include_candidates:
            for namespace in namespaces:
                candidates.extend(self.store.list_candidates(namespace=namespace, status="pending")[: request.limit])
        if records:
            self._update_run_memory_refs(request.run_id, used=[record.memory_id for record in records], warnings=warnings)
            self._event(request.run_id, "memory_search_completed", "Busca de memoria retornou contexto governado.", {"count": len(records), "warnings": sorted(set(warnings))}, evidence_refs=[f"memory:{record.memory_id}" for record in records])
        return MemorySearchResult(status="ok", records=records, candidates=candidates, warnings=sorted(set(warnings)), access_logs=access_logs)

    def load_context_for_run(self, request: MemoryContextLoadRequest) -> MemoryContextLoadResult:
        namespaces = [
            PRIVATE_NAMESPACE_BY_AGENT.get(request.agent_id, ""),
            "memory:shared",
            "memory:project",
            "memory:regression",
            "memory:user_preferences",
        ]
        search = self.search(
            MemorySearchRequest(
                agent_id=request.agent_id,
                namespaces=[namespace for namespace in namespaces if namespace],
                workspace_id=request.workspace_id,
                project_id=request.project_id,
                include_stale=True,
                limit=request.limit,
                session_id=request.session_id,
                run_id=request.run_id,
                reason=request.reason,
            )
        )
        chunks: list[str] = []
        total = 0
        selected: list[MemoryRecord] = []
        for record in search.records:
            text = f"[{record.namespace}] {record.title}: {record.content_sanitized}"
            if total + len(text) > request.max_chars:
                break
            chunks.append(text)
            total += len(text)
            selected.append(record)
        refs = [record.memory_id for record in selected]
        if request.run_id:
            self._event(request.run_id, "memory_context_loaded", "Contexto de memoria carregado para run.", {"memory_refs": refs, "warnings": search.warnings}, evidence_refs=[f"memory:{memory_id}" for memory_id in refs])
            self._update_run_memory_refs(request.run_id, used=refs, warnings=search.warnings)
        return MemoryContextLoadResult(status="ok", agent_id=request.agent_id, run_id=request.run_id, memory_refs_used=refs, records=selected, warnings=search.warnings, context_sanitized="\n".join(chunks))

    def run_memory(self, run_id: str) -> dict[str, Any]:
        run = self.kernel.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        return {
            "status": "ok",
            "run_id": run_id,
            "agent_id": run.agent_id,
            "memory_refs_used": run.memory_refs_used,
            "memory_refs_written": run.memory_refs_written,
            "memory_candidates_created": run.memory_candidates_created,
            "memory_warnings": run.memory_warnings,
            "access_logs": self.store.list_access(run_id=run_id),
        }

    def update_record(self, memory_id: str, payload: dict[str, Any], *, agent_id: str) -> tuple[MemoryRecord, Any]:
        memory = self.store.get_record(memory_id)
        if memory is None:
            raise FileNotFoundError(memory_id)
        allowed = {
            key: value
            for key, value in payload.items()
            if key
            in {
                "title",
                "content_sanitized",
                "tags",
                "confidence",
                "freshness",
                "validation_status",
                "metadata_sanitized",
            }
        }
        candidate = memory.model_copy(update=allowed)
        policy = self.policy.evaluate_write(
            MemoryWriteRequest(
                agent_id=agent_id,
                namespace=candidate.namespace,
                scope=candidate.scope,
                title=candidate.title,
                content_sanitized=candidate.content_sanitized,
                memory_type=candidate.memory_type,
                source_type=candidate.source_type,
                source_ref=candidate.source_ref,
                evidence_refs=candidate.evidence_refs,
                confidence=candidate.confidence,
                validation_status=candidate.validation_status,
                tags=candidate.tags,
                project_id=candidate.project_id,
                workspace_id=candidate.workspace_id,
                supersedes=candidate.supersedes,
                reason="memory_record_update",
                metadata_sanitized=candidate.metadata_sanitized,
            )
        )
        if policy.decision == "deny":
            self._access(memory_id, None, agent_id, "update", policy.reason_code, None, None, {"fields": sorted(allowed)})
            raise PermissionError(policy.reason_code)
        redacted_updates = {
            "updated_at": utc_now_iso(),
            "content_sanitized": str(redact_payload(candidate.content_sanitized)),
            "metadata_sanitized": redact_payload(candidate.metadata_sanitized),
        }
        updated = self.store.save_record(candidate.model_copy(update=redacted_updates))
        self._access(updated.memory_id, None, agent_id, "update", policy.reason_code, None, None, {"fields": sorted(allowed)})
        return updated, policy

    def supersede(self, memory_id: str, request: MemorySupersedeRequest) -> MemoryRecord:
        memory = self.store.get_record(memory_id)
        if memory is None:
            raise FileNotFoundError(memory_id)
        replacement = self.store.get_record(request.replacement_memory_id) if request.replacement_memory_id else None
        memory = memory.model_copy(update={"validation_status": "superseded", "freshness": "stale", "superseded_by": replacement.memory_id if replacement else None})
        memory = self.store.save_record(memory)
        self._access(memory.memory_id, None, request.agent_id, "supersede", request.reason, None, None, {"replacement_memory_id": request.replacement_memory_id})
        return memory

    def _detect_contradictions(self, record: MemoryRecord) -> list[str]:
        refs: list[str] = []
        comparable = self.store.list_records(namespace=record.namespace)
        for existing in comparable:
            if existing.memory_id == record.memory_id or existing.validation_status in {"superseded", "rejected"}:
                continue
            same_scope = existing.workspace_id == record.workspace_id and existing.project_id == record.project_id
            same_title = existing.title.strip().lower() == record.title.strip().lower()
            if same_scope and same_title and existing.content_sanitized.strip() != record.content_sanitized.strip():
                refs.append(existing.memory_id)
        return refs

    def _update_run_memory_refs(self, run_id: str | None, *, used: list[str] | None = None, written: list[str] | None = None, candidates: list[str] | None = None, warnings: list[str] | None = None) -> None:
        if not run_id:
            return
        run = self.kernel.get_run(run_id)
        if run is None:
            return
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                memory_refs_used=sorted(set([*run.memory_refs_used, *(used or [])])) or None,
                memory_refs_written=sorted(set([*run.memory_refs_written, *(written or [])])) or None,
                memory_candidates_created=sorted(set([*run.memory_candidates_created, *(candidates or [])])) or None,
                memory_warnings=sorted(set([*run.memory_warnings, *(warnings or [])])) or None,
            ),
        )

    def _event(self, run_id: str | None, event_type: str, message: str, payload: dict[str, Any], *, severity: str = "info", evidence_refs: list[str] | None = None) -> None:
        if not run_id:
            return
        if self.kernel.get_run(run_id) is None:
            return
        self.kernel.add_event(
            run_id,
            AgentEventCreateRequest(
                event_type=event_type,
                severity=severity,
                human_message=message,
                technical_summary_sanitized=event_type,
                payload_sanitized=redact_payload(payload),
                evidence_refs=evidence_refs or [],
                visible_in_timeline=event_type in {"memory_context_loaded", "memory_contradiction_detected", "memory_access_denied"},
            ),
        )

    def _access(self, memory_id: str | None, candidate_id: str | None, agent_id: str, access_type: str, reason: str, session_id: str | None, run_id: str | None, metadata: dict[str, Any]) -> MemoryAccessLog:
        return self.store.append_access(
            MemoryAccessLog(
                memory_id=memory_id,
                candidate_id=candidate_id,
                agent_id=agent_id,
                session_id=session_id,
                run_id=run_id,
                access_type=access_type,  # type: ignore[arg-type]
                reason=reason,
                metadata_sanitized=redact_payload(metadata),
            )
        )

    def _scope_for_namespace(self, namespace: str):
        return {
            "memory:shared": "shared",
            "memory:project": "project",
            "memory:regression": "regression",
            "memory:user_preferences": "user_preference",
            "memory:security": "security",
        }.get(namespace, "private")

    def _freshness_for(self, memory_type: str):
        return "recent" if memory_type in {"command", "validation_result"} else "fresh"

    def _max_record_chars(self) -> int:
        return int(self.policy.config().get("max_record_chars", 12000))
