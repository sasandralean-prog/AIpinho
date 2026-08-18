from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.schemas.memory.memory_candidate import (
    MemoryCandidate,
    MemoryCandidateRequest,
    MemoryCandidateResult,
    MemoryCandidateTrace,
    MemoryExtractionResult,
)
from aipinho.services.memory.memory_candidate_classifier import MemoryCandidateClassifier
from aipinho.services.memory.memory_candidate_conflict_service import MemoryCandidateConflictService
from aipinho.services.memory.memory_candidate_dedupe_service import MemoryCandidateDedupeService
from aipinho.services.memory.memory_candidate_evidence_service import MemoryCandidateEvidenceService
from aipinho.services.memory.memory_candidate_extractor import MemoryCandidateExtractor
from aipinho.services.memory.memory_candidate_risk_service import MemoryCandidateRiskService
from aipinho.services.memory.memory_candidate_scope_service import MemoryCandidateScopeService
from aipinho.services.memory.memory_candidate_sensitivity_scanner import MemoryCandidateSensitivityScanner
from aipinho.services.memory.memory_candidate_source_resolver import MemoryCandidateSourceResolver
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from aipinho.services.memory.memory_candidate_validator import MemoryCandidateValidator
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file
from aipinho.core.paths import PATHS


class MemoryCandidateService:
    CONFIGS = [
        "memory_candidate_policy.yaml",
        "memory_candidate_source_policy.yaml",
        "memory_candidate_extraction_policy.yaml",
        "memory_candidate_validation_policy.yaml",
        "memory_candidate_scope_policy.yaml",
        "memory_candidate_evidence_policy.yaml",
        "memory_candidate_risk_policy.yaml",
        "memory_candidate_dedupe_policy.yaml",
        "memory_candidate_conflict_policy.yaml",
        "memory_candidate_sensitivity_policy.yaml",
        "memory_candidate_store_policy.yaml",
        "memory_candidate_audit_policy.yaml",
        "memory_candidate_lifecycle_policy.yaml",
    ]

    def __init__(self, store: MemoryCandidateStore | None = None) -> None:
        self.store = store or MemoryCandidateStore()
        self.policy = load_yaml_file(PATHS.config_root / "memory" / "memory_candidate_policy.yaml", critical=True, root=PATHS.config_root / "memory")
        self.source_resolver = MemoryCandidateSourceResolver()
        self.classifier = MemoryCandidateClassifier()
        self.scope = MemoryCandidateScopeService()
        self.evidence = MemoryCandidateEvidenceService()
        self.sensitivity = MemoryCandidateSensitivityScanner()
        self.dedupe = MemoryCandidateDedupeService()
        self.conflict = MemoryCandidateConflictService()
        self.risk = MemoryCandidateRiskService()
        self.validator = MemoryCandidateValidator()
        self.extractor = MemoryCandidateExtractor()

    def create_candidate(self, request: MemoryCandidateRequest) -> MemoryCandidateResult:
        now = utc_now()
        trace: list[MemoryCandidateTrace] = []
        warnings: list[str] = []
        blocked_reasons: list[str] = []
        requested_status = (request.status or "candidate").lower()
        kind = self.classifier.classify(request.text, request.kind)
        source = self.source_resolver.resolve(request.source, metadata=request.metadata)
        scope = self.scope.resolve(request.scope, kind=kind, text=request.text)
        evidence = self.evidence.build(request.evidence, source=source, text=request.text, kind=kind)
        sensitivity = self.sensitivity.scan(request.text, evidence=evidence)
        existing = self.store.list_candidates(limit=1000)
        dedupe = self.dedupe.evaluate(request.text, kind=kind, scope=scope, existing=existing)
        conflict = self.conflict.evaluate(request.text, kind=kind, scope=scope, existing=existing)
        risk = self.risk.evaluate(source=source, scope=scope, evidence=evidence, sensitivity=sensitivity, conflict=conflict, kind=kind)
        validation = self.validator.validate(
            text=request.text,
            requested_status=requested_status,
            kind=kind,
            source=source,
            scope=scope,
            evidence=evidence,
            sensitivity=sensitivity,
            dedupe=dedupe,
            conflict=conflict,
            risk=risk,
        )
        if not validation.passed:
            blocked_reasons.extend(validation.reasons)
        if sensitivity.status != "safe":
            warnings.extend(sensitivity.reasons)
        if requested_status == "approved":
            warnings.append("approved_state_forbidden_this_sprint")
        if dedupe.status in {"duplicate", "near_duplicate"}:
            warnings.append(dedupe.status)
        if conflict.has_conflict:
            warnings.extend(conflict.reasons)
        status = self._status_from(validation, requested_status, dedupe.status, conflict.has_conflict, risk.level)
        summary = (request.summary or self._summarize(request.text)).strip()
        sanitized_text = sensitivity.redacted_text if sensitivity.status in {"needs_redaction", "blocked"} else request.text.strip()
        candidate = MemoryCandidate(
            candidate_id=f"memcand_{uuid4().hex}",
            status=status,
            kind=kind,
            text=sanitized_text[:1200],
            summary=summary[:500],
            source=source,
            scope=scope,
            evidence=evidence,
            confidence=self.evidence.confidence(evidence=evidence, source=source, kind=kind),
            risk=risk,
            validation=validation,
            dedupe=dedupe,
            conflict=conflict,
            trace=[
                MemoryCandidateTrace(stage="source", status="ok" if source.trusted else "needs_review", reason=source.source_type),
                MemoryCandidateTrace(stage="sensitivity", status=sensitivity.status, reason=";".join(sensitivity.reasons) or "safe"),
                MemoryCandidateTrace(stage="dedupe", status=dedupe.status, reason=dedupe.matched_candidate_id or "unique"),
                MemoryCandidateTrace(stage="validation", status=validation.status, reason=";".join(validation.reasons) or "passed"),
                *trace,
            ],
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            created_at=now,
            updated_at=now,
        )
        saved = self.store.save_candidate(candidate)
        self.store.append_event(saved.candidate_id, "candidate_created", saved.status, "Memory candidate created in candidate-only mode.", {"kind": saved.kind})
        self.store.save_trace(saved.candidate_id, saved.trace)
        return MemoryCandidateResult(status=saved.status, candidate=saved, warnings=saved.warnings)

    def extract_candidates(self, source_type: str, source_id: str | None = None, payload: dict[str, Any] | None = None) -> MemoryExtractionResult:
        source, requests = self.extractor.extract(source_type=source_type, source_id=source_id, payload=payload or {})
        candidates = [self.create_candidate(request).candidate for request in requests]
        return MemoryExtractionResult(status="ok", source=source, candidates=[item for item in candidates if item is not None])

    def get_candidate(self, candidate_id: str) -> MemoryCandidate | None:
        return self.store.get_candidate(candidate_id)

    def list_candidates(self, **filters: Any) -> list[MemoryCandidate]:
        return self.store.list_candidates(**filters)

    def reject_candidate(self, candidate_id: str, reason: str = "user_rejected") -> MemoryCandidate | None:
        updated = self.store.update_candidate_status(candidate_id, "rejected", reason)
        if updated:
            self.store.append_event(candidate_id, "candidate_rejected", "rejected", reason)
        return updated

    def mark_duplicate(self, candidate_id: str, duplicate_of: str | None = None, reason: str = "marked_duplicate") -> MemoryCandidate | None:
        updated = self.store.update_candidate_status(candidate_id, "duplicate", reason)
        if updated:
            self.store.append_event(candidate_id, "candidate_marked_duplicate", "duplicate", reason, {"duplicate_of": duplicate_of})
        return updated

    def refresh_validation(self, candidate_id: str) -> MemoryCandidate | None:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            return None
        request = MemoryCandidateRequest(text=candidate.text, summary=candidate.summary, kind=candidate.kind, source=candidate.source, scope=candidate.scope, evidence=candidate.evidence, metadata={"refresh_of": candidate_id})
        refreshed = self.create_candidate(request).candidate
        if refreshed is None:
            return candidate
        candidate.validation = refreshed.validation
        candidate.risk = refreshed.risk
        candidate.warnings = refreshed.warnings
        candidate.blocked_reasons = refreshed.blocked_reasons
        candidate.updated_at = utc_now()
        self.store.save_candidate(candidate)
        self.store.append_event(candidate_id, "candidate_revalidated", candidate.status, "Memory candidate validation refreshed.")
        return candidate

    def get_evidence(self, candidate_id: str):
        candidate = self.get_candidate(candidate_id)
        return [] if candidate is None else candidate.evidence

    def get_trace(self, candidate_id: str):
        return self.store.get_trace(candidate_id)

    def get_events(self, candidate_id: str):
        return self.store.get_events(candidate_id)

    def status(self) -> dict[str, Any]:
        root = PATHS.config_root / "memory"
        configs = {name: inspect_yaml_file(root / name, root=PATHS.project_root).__dict__ for name in self.CONFIGS}
        warnings = [f"{name}:{value.get('status')}" for name, value in configs.items() if value.get("status") != "ok"]
        counts: dict[str, int] = {}
        for candidate in self.store.list_candidates(limit=10000):
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return {
            "status": "degraded" if warnings else "ok",
            "service": "memory_candidate",
            "memory_candidate_enabled": True,
            "memory_mode": "candidate_only",
            "approved_memory_enabled": False,
            "vectorstore_enabled": False,
            "embeddings_enabled": False,
            "rag_enabled": False,
            "auto_memory_enabled": False,
            "chat_can_approve_memory": False,
            "store": self.store.status(),
            "counts_by_status": counts,
            "allowed_kinds": self.policy.get("allowed_memory_kinds", []),
            "configs": configs,
            "warnings": warnings,
        }

    def _status_from(self, validation, requested_status: str, dedupe_status: str, has_conflict: bool, risk_level: str) -> str:
        if requested_status == "approved" or not validation.passed or risk_level == "critical":
            return "blocked"
        if dedupe_status == "duplicate":
            return "duplicate"
        if dedupe_status == "near_duplicate" or has_conflict or risk_level in {"medium", "high"}:
            return "needs_review"
        return "candidate"

    def _summarize(self, text: str) -> str:
        compact = " ".join(text.strip().split())
        return compact[:500] if compact else "Memory candidate without summary."
