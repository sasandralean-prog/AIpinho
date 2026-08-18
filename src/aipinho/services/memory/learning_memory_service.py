from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.memory.learning import (
    ArtifactLearningRecord,
    CommandLearningRecord,
    FailurePatternRecord,
    LearningExtractionRequest,
    LearningExtractionResult,
    LearningStatus,
    MemoryCandidateV2,
    MemoryQuery,
    MemoryRecord,
    MemoryReviewQueue,
    ProjectLearningProfile,
    RunLearningSummary,
    SkillPackLearningProfile,
    TemplateLearningProfile,
    TemplateLearningRecord,
)
from aipinho.services.events.event_core import contains_secret, redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class LearningMemoryService:
    def __init__(self, root: Path | None = None, policy_path: Path | None = None) -> None:
        env_root = os.environ.get("AIPINHO_LEARNING_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "learning")
        self.policy_path = policy_path or PATHS.config_root / "memory" / "learning_policy.yaml"
        self.root.mkdir(parents=True, exist_ok=True)
        self.extractions_path = self.root / "extractions.json"
        self.run_summaries_path = self.root / "run_summaries.json"
        self.candidates_path = self.root / "candidates.json"
        self.memories_path = self.root / "memories.json"
        self.project_profiles_path = self.root / "project_profiles.json"
        self.skill_pack_profiles_path = self.root / "skill_pack_profiles.json"
        self.template_profiles_path = self.root / "template_profiles.json"

    def status(self) -> LearningStatus:
        return LearningStatus(
            status="ok" if self._policy().get("learning_enabled", True) else "disabled",
            candidates=len(self.list_candidates(include_all=True)),
            accepted_memories=len(self._memories()),
            run_summaries=len(self.list_run_summaries()),
        )

    def extract(self, request: LearningExtractionRequest) -> LearningExtractionResult:
        policy = self._policy()
        warnings: list[str] = []
        blocked_reasons: list[str] = []
        sanitized_request = request.model_copy(update={"metadata_sanitized": self._sanitize_metadata(request.metadata_sanitized)})
        payload = sanitized_request.model_dump()
        if contains_secret(request.model_dump()):
            blocked_reasons.append("secret_detected")
        if self._contains_blocked_payload(payload, policy):
            blocked_reasons.append("raw_or_stacktrace_payload_blocked")
        if not sanitized_request.evidence_refs and bool(policy.get("evidence_required", True)):
            blocked_reasons.append("learning_evidence_required")

        summary = RunLearningSummary(
            source_type=sanitized_request.source_type,
            source_id=sanitized_request.source_id,
            agent_id=sanitized_request.agent_id,
            session_id=sanitized_request.session_id,
            run_id=sanitized_request.run_id,
            project_id=sanitized_request.project_id,
            skill_pack_id=sanitized_request.skill_pack_id,
            template_id=sanitized_request.template_id,
            outcome=sanitized_request.outcome or "unknown",
            what_worked=[self._as_text(item) for item in sanitized_request.what_worked],
            what_failed=[self._as_text(item) for item in sanitized_request.what_failed],
            commands_successful=[self._as_text(item) for item in sanitized_request.commands_successful],
            commands_failed=[self._as_text(item) for item in sanitized_request.commands_failed],
            validations_run=[self._as_text(item) for item in sanitized_request.validations_run],
            artifacts_created=[self._as_text(item) for item in sanitized_request.artifacts_created],
            blocked_reason_codes=blocked_reasons,
            evidence_refs=sanitized_request.evidence_refs,
            metadata_sanitized=sanitized_request.metadata_sanitized,
        )
        candidates = self._build_candidates(sanitized_request, summary, blocked_reasons)
        summary = summary.model_copy(update={"candidate_ids": [candidate.candidate_id for candidate in candidates]})
        result = LearningExtractionResult(
            status="blocked" if blocked_reasons else "candidates_created" if candidates else "no_candidates",
            run_summary=summary,
            candidates=candidates,
            blocked_reason_codes=blocked_reasons,
            warnings=warnings,
            trace_refs=[f"run_summary:{summary.run_summary_id}", *[f"memory_candidate:{item.candidate_id}" for item in candidates]],
        )
        self._save_run_summary(summary)
        for candidate in candidates:
            self._save_candidate(candidate)
            self._update_profiles_for_candidate(candidate)
        self._save_extraction(result)
        return result

    def get_extraction(self, extraction_id: str) -> LearningExtractionResult | None:
        return next((item for item in self._extractions() if item.extraction_id == extraction_id), None)

    def list_run_summaries(self, *, project_id: str | None = None, skill_pack_id: str | None = None, limit: int = 100) -> list[RunLearningSummary]:
        rows = self._run_summaries()
        if project_id:
            rows = [item for item in rows if item.project_id == project_id]
        if skill_pack_id:
            rows = [item for item in rows if item.skill_pack_id == skill_pack_id]
        return rows[-max(1, min(limit, 1000)) :]

    def get_run_summary(self, run_summary_id: str) -> RunLearningSummary | None:
        return next((item for item in self._run_summaries() if item.run_summary_id == run_summary_id), None)

    def list_candidates(
        self,
        *,
        status: str | None = None,
        type: str | None = None,
        project_id: str | None = None,
        skill_pack_id: str | None = None,
        template_id: str | None = None,
        include_all: bool = False,
        limit: int = 100,
    ) -> list[MemoryCandidateV2]:
        rows = self._candidates()
        if not include_all and status is None:
            rows = [item for item in rows if item.status in {"proposed", "needs_review", "blocked"}]
        if status:
            rows = [item for item in rows if item.status == status]
        if type:
            rows = [item for item in rows if item.type == type]
        if project_id:
            rows = [item for item in rows if item.project_id == project_id]
        if skill_pack_id:
            rows = [item for item in rows if item.skill_pack_id == skill_pack_id]
        if template_id:
            rows = [item for item in rows if item.template_id == template_id]
        return rows[-max(1, min(limit, 1000)) :]

    def get_candidate(self, candidate_id: str) -> MemoryCandidateV2 | None:
        return next((item for item in self._candidates() if item.candidate_id == candidate_id), None)

    def accept_candidate(self, candidate_id: str, *, reviewed_by: str = "codex", reason: str = "") -> dict[str, Any]:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        block_reasons = self._accept_block_reasons(candidate)
        if block_reasons:
            candidate = candidate.model_copy(update={"status": "blocked", "block_reason_codes": list(dict.fromkeys([*candidate.block_reason_codes, *block_reasons])), "updated_at": utc_now_iso()})
            self._save_candidate(candidate)
            return {"status": "blocked", "candidate": candidate, "blocked_reason_codes": block_reasons}
        record = MemoryRecord(
            candidate_id=candidate.candidate_id,
            type=candidate.type,
            title=candidate.title,
            summary=candidate.summary,
            reusable_when=candidate.reusable_when,
            scope=candidate.scope,
            confidence=candidate.confidence,
            evidence_refs=candidate.evidence_refs,
            source_refs=candidate.source_refs,
            project_id=candidate.project_id,
            skill_pack_id=candidate.skill_pack_id,
            template_id=candidate.template_id,
            tags=candidate.tags,
            accepted_by=reviewed_by,
            metadata_sanitized={"accepted_reason": reason, **candidate.metadata_sanitized},
        )
        candidate = candidate.model_copy(update={"status": "accepted", "memory_id": record.memory_id, "updated_at": utc_now_iso()})
        self._save_memory(record)
        self._save_candidate(candidate)
        self._update_profiles_for_memory(record, candidate)
        return {"status": "accepted", "candidate": candidate, "memory": record}

    def reject_candidate(self, candidate_id: str, *, reviewed_by: str = "codex", reason: str = "") -> MemoryCandidateV2:
        return self._set_candidate_status(candidate_id, "rejected", reviewed_by, reason)

    def archive_candidate(self, candidate_id: str, *, reviewed_by: str = "codex", reason: str = "") -> MemoryCandidateV2:
        return self._set_candidate_status(candidate_id, "archived", reviewed_by, reason)

    def mark_stale(self, candidate_id: str, *, reviewed_by: str = "codex", reason: str = "") -> MemoryCandidateV2:
        return self._set_candidate_status(candidate_id, "stale", reviewed_by, reason)

    def query(self, request: MemoryQuery) -> dict[str, Any]:
        memories = self._memories()
        if request.status and request.status != "all":
            memories = [item for item in memories if item.status == request.status]
        if request.type:
            memories = [item for item in memories if item.type == request.type]
        if request.project_id:
            memories = [item for item in memories if item.project_id == request.project_id]
        if request.skill_pack_id:
            memories = [item for item in memories if item.skill_pack_id == request.skill_pack_id]
        if request.template_id:
            memories = [item for item in memories if item.template_id == request.template_id]
        if request.confidence:
            memories = [item for item in memories if item.confidence == request.confidence]
        tags = {tag.casefold() for tag in request.tags}
        if tags:
            memories = [item for item in memories if tags.intersection({tag.casefold() for tag in item.tags})]
        if request.query:
            terms = [term for term in request.query.casefold().split() if term]
            memories = [
                item for item in memories
                if all(term in f"{item.title} {item.summary} {' '.join(item.tags)}".casefold() for term in terms)
            ]
        limit = max(1, min(request.limit, 100))
        return {"status": "ok", "results": memories[:limit], "total": len(memories)}

    def namespaces(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "namespaces": [
                {"namespace": "learning:project", "scope": "project", "evidence_required": True},
                {"namespace": "learning:skill_pack", "scope": "skill_pack", "evidence_required": True},
                {"namespace": "learning:template", "scope": "template", "evidence_required": True},
                {"namespace": "learning:regression", "scope": "regression", "evidence_required": True},
                {"namespace": "learning:global_guarded", "scope": "global_guarded", "evidence_required": True, "review_required": True},
            ],
        }

    def review_queue(self) -> MemoryReviewQueue:
        rows = self.list_candidates(include_all=False)
        counts: dict[str, int] = {}
        for candidate in rows:
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return MemoryReviewQueue(candidates=rows, counts=counts)

    def project_profile(self, project_id: str) -> ProjectLearningProfile:
        return self._project_profiles().get(project_id) or ProjectLearningProfile(project_id=project_id)

    def skill_pack_profile(self, skill_pack_id: str) -> SkillPackLearningProfile:
        return self._skill_pack_profiles().get(skill_pack_id) or SkillPackLearningProfile(skill_pack_id=skill_pack_id)

    def template_profile(self, template_id: str) -> TemplateLearningProfile:
        return self._template_profiles().get(template_id) or TemplateLearningProfile(template_id=template_id)

    def mobile_memory_view_model(self) -> dict[str, Any]:
        queue = self.review_queue()
        accepted = self._memories()[-20:]
        return {
            "state": {
                "screen": "memory_learning",
                "status": "ok",
                "raw_default_visible": False,
                "human_summary": "Memoria operacional curada exige evidencia e revisao.",
            },
            "review_queue": [_dump(item) for item in queue.candidates],
            "accepted_recent": [_dump(item) for item in accepted],
            "counts": queue.counts,
            "actions": [
                {"label": "Aceitar", "endpoint": "/api/v1/memory/candidates/{candidate_id}/accept"},
                {"label": "Rejeitar", "endpoint": "/api/v1/memory/candidates/{candidate_id}/reject"},
                {"label": "Arquivar", "endpoint": "/api/v1/memory/candidates/{candidate_id}/archive"},
            ],
        }

    def mobile_learning_view_model(self) -> dict[str, Any]:
        summaries = self.list_run_summaries(limit=20)
        return {
            "state": {
                "screen": "learning_from_runs",
                "status": "ok",
                "raw_default_visible": False,
                "human_summary": "Aprendizado operacional extraido de runs com evidencia.",
            },
            "run_summaries": [_dump(item) for item in summaries],
            "status_detail": self.status().model_dump(),
        }

    def _policy(self) -> dict[str, Any]:
        data = load_yaml_file(self.policy_path, critical=False, root=PATHS.project_root)
        return data if isinstance(data, dict) else {}

    def _build_candidates(self, request: LearningExtractionRequest, summary: RunLearningSummary, blocked_reasons: list[str]) -> list[MemoryCandidateV2]:
        rows: list[MemoryCandidateV2] = []
        evidence = list(request.evidence_refs)
        common = {
            "source_type": request.source_type,
            "source_id": request.source_id,
            "source_refs": [ref for ref in [request.source_id, request.run_id, request.session_id] if ref],
            "evidence_refs": evidence,
            "project_id": request.project_id,
            "skill_pack_id": request.skill_pack_id,
            "template_id": request.template_id,
            "artifact_ids": request.artifact_ids,
            "tags": request.tags,
            "contains_secret_risk": "secret_detected" in blocked_reasons,
            "raw_log_blocked": "raw_or_stacktrace_payload_blocked" in blocked_reasons,
            "block_reason_codes": blocked_reasons,
            "status": "blocked" if blocked_reasons else "proposed",
            "scope": self._scope_for(request),
            "metadata_sanitized": request.metadata_sanitized,
        }
        for lesson in request.reusable_lessons:
            payload = self._lesson_payload(lesson)
            rows.append(self._candidate(
                type=str(payload.get("type") or "workflow_lesson"),
                title=str(payload.get("title") or "Licao reutilizavel de run"),
                summary=str(payload.get("summary") or payload.get("lesson") or lesson),
                reusable_when=[str(item) for item in payload.get("reusable_when", [])] if isinstance(payload.get("reusable_when"), list) else [],
                common=common,
            ))
        for command in request.commands_successful:
            text = self._as_text(command)
            rows.append(self._candidate(type="command_learning", title="Comando validado em run", summary=text, reusable_when=["command_execution"], common=common))
        for command in request.commands_failed:
            text = self._as_text(command)
            rows.append(self._candidate(type="failure_pattern", title="Falha de comando observada", summary=text, reusable_when=["debugging", "command_execution"], common=common))
        for failure in request.what_failed:
            rows.append(self._candidate(type="failure_pattern", title="Padrao de falha observado", summary=self._as_text(failure), reusable_when=["debugging", "regression"], common=common))
        for artifact in request.artifacts_created:
            text = self._as_text(artifact)
            rows.append(self._candidate(type="artifact_learning", title="Licao de artifact criado", summary=text, reusable_when=["artifact_lifecycle"], common=common))
        if request.skill_pack_id and (request.what_worked or request.what_failed):
            rows.append(self._candidate(type="skill_pack_learning", title=f"Aprendizado do skill pack {request.skill_pack_id}", summary=self._summary_text(request), reusable_when=["skill_pack_selection", "skill_execution"], common=common))
        if request.template_id and (request.what_worked or request.what_failed):
            rows.append(self._candidate(type="template_learning", title=f"Aprendizado do template {request.template_id}", summary=self._summary_text(request), reusable_when=["template_selection", "project_generation"], common=common))
        deduped: list[MemoryCandidateV2] = []
        seen = {self._fingerprint(item) for item in self._candidates()}
        current: set[str] = set()
        for candidate in rows:
            fingerprint = self._fingerprint(candidate)
            if fingerprint in seen or fingerprint in current:
                candidate = candidate.model_copy(update={"status": "superseded", "warnings": [*candidate.warnings, "duplicate_candidate"]})
            current.add(fingerprint)
            deduped.append(candidate)
        return deduped

    def _candidate(self, *, type: str, title: str, summary: str, reusable_when: list[str], common: dict[str, Any]) -> MemoryCandidateV2:
        allowed = set(self._policy().get("allowed_candidate_types", []))
        candidate_type = type if type in allowed else "workflow_lesson"
        return MemoryCandidateV2(
            type=candidate_type,  # type: ignore[arg-type]
            title=title[:240],
            summary=str(redact_payload(summary))[: int(self._policy().get("max_candidate_summary_chars", 2000))],
            reusable_when=reusable_when,
            **common,
        )

    def _scope_for(self, request: LearningExtractionRequest) -> str:
        if request.project_id:
            return "project"
        if request.skill_pack_id:
            return "skill_pack"
        if request.template_id:
            return "template"
        if request.artifact_ids:
            return "artifact"
        return "global_guarded"

    def _accept_block_reasons(self, candidate: MemoryCandidateV2) -> list[str]:
        reasons = list(candidate.block_reason_codes)
        if not candidate.evidence_refs:
            reasons.append("learning_evidence_required")
        if candidate.contains_secret_risk:
            reasons.append("secret_detected")
        if candidate.raw_log_blocked:
            reasons.append("raw_log_not_accepted")
        if candidate.status in {"rejected", "archived"}:
            reasons.append(f"candidate_{candidate.status}")
        return list(dict.fromkeys(reasons))

    def _set_candidate_status(self, candidate_id: str, status: str, reviewed_by: str, reason: str) -> MemoryCandidateV2:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        updated = candidate.model_copy(update={"status": status, "updated_at": utc_now_iso(), "metadata_sanitized": {**candidate.metadata_sanitized, "reviewed_by": reviewed_by, "review_reason": reason}})
        self._save_candidate(updated)
        return updated

    def _update_profiles_for_candidate(self, candidate: MemoryCandidateV2) -> None:
        if candidate.project_id:
            profile = self.project_profile(candidate.project_id)
            self._save_project_profile(profile.model_copy(update={"candidate_ids": self._append_unique(profile.candidate_ids, candidate.candidate_id), "updated_at": utc_now_iso()}))
        if candidate.skill_pack_id:
            profile = self.skill_pack_profile(candidate.skill_pack_id)
            self._save_skill_pack_profile(profile.model_copy(update={"candidate_ids": self._append_unique(profile.candidate_ids, candidate.candidate_id), "updated_at": utc_now_iso()}))
        if candidate.template_id:
            profile = self.template_profile(candidate.template_id)
            self._save_template_profile(profile.model_copy(update={"candidate_ids": self._append_unique(profile.candidate_ids, candidate.candidate_id), "updated_at": utc_now_iso()}))

    def _update_profiles_for_memory(self, record: MemoryRecord, candidate: MemoryCandidateV2) -> None:
        if record.project_id:
            profile = self.project_profile(record.project_id)
            updates = {"accepted_memory_ids": self._append_unique(profile.accepted_memory_ids, record.memory_id), "updated_at": utc_now_iso()}
            if record.type == "command_learning":
                updates["successful_commands"] = self._append_unique(profile.successful_commands, record.title)
            if record.type == "failure_pattern":
                updates["failure_patterns"] = self._append_unique(profile.failure_patterns, record.title)
            if record.type == "artifact_learning":
                updates["artifact_lessons"] = self._append_unique(profile.artifact_lessons, record.title)
            self._save_project_profile(profile.model_copy(update=updates))
        if record.skill_pack_id:
            profile = self.skill_pack_profile(record.skill_pack_id)
            self._save_skill_pack_profile(profile.model_copy(update={
                "accepted_memory_ids": self._append_unique(profile.accepted_memory_ids, record.memory_id),
                "success_count": profile.success_count + (1 if candidate.type != "failure_pattern" else 0),
                "failure_count": profile.failure_count + (1 if candidate.type == "failure_pattern" else 0),
                "updated_at": utc_now_iso(),
            }))
        if record.template_id:
            profile = self.template_profile(record.template_id)
            self._save_template_profile(profile.model_copy(update={
                "accepted_memory_ids": self._append_unique(profile.accepted_memory_ids, record.memory_id),
                "success_count": profile.success_count + (1 if candidate.type != "failure_pattern" else 0),
                "failure_count": profile.failure_count + (1 if candidate.type == "failure_pattern" else 0),
                "updated_at": utc_now_iso(),
            }))

    def _contains_blocked_payload(self, value: Any, policy: dict[str, Any]) -> bool:
        blocked_keys = {str(item).casefold() for item in policy.get("blocked_payload_keys", [])}
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key).casefold()
                if key_text in blocked_keys:
                    return True
                if self._contains_blocked_payload(item, policy):
                    return True
        if isinstance(value, list):
            return any(self._contains_blocked_payload(item, policy) for item in value)
        if isinstance(value, str):
            lowered = value.casefold()
            return "traceback (most recent call last)" in lowered or "stacktrace" in lowered
        return False

    def _sanitize_metadata(self, value: Any) -> Any:
        sensitive_key_fragments = ("token", "secret", "api_key", "apikey", "password", "credential")
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if any(fragment in key_text.casefold() for fragment in sensitive_key_fragments):
                    sanitized[key_text] = "[REDACTED_SECRET]"
                else:
                    sanitized[key_text] = self._sanitize_metadata(item)
            return redact_payload(sanitized)
        if isinstance(value, list):
            return [self._sanitize_metadata(item) for item in value]
        return redact_payload(value)

    def _lesson_payload(self, value: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(value, dict):
            return redact_payload(value)
        return {"summary": str(redact_payload(value))}

    def _summary_text(self, request: LearningExtractionRequest) -> str:
        parts = [*request.what_worked, *request.what_failed]
        return "; ".join(self._as_text(item) for item in parts) or str(request.outcome or "run learning")

    def _as_text(self, value: Any) -> str:
        if isinstance(value, str):
            return str(redact_payload(value))
        return json.dumps(redact_payload(value), ensure_ascii=True, sort_keys=True)

    def _fingerprint(self, candidate: MemoryCandidateV2) -> str:
        text = f"{candidate.type}|{candidate.project_id}|{candidate.skill_pack_id}|{candidate.template_id}|{candidate.title}|{candidate.summary}".casefold()
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _append_unique(self, values: list[str], value: str) -> list[str]:
        return [*values, value] if value not in values else values

    def _extractions(self) -> list[LearningExtractionResult]:
        return [LearningExtractionResult(**item) for item in _read_json(self.extractions_path, {"extractions": []}).get("extractions", [])]

    def _save_extraction(self, extraction: LearningExtractionResult) -> None:
        rows = [item for item in self._extractions() if item.extraction_id != extraction.extraction_id]
        rows.append(extraction)
        _write_json(self.extractions_path, {"extractions": [_dump(item) for item in rows]})

    def _run_summaries(self) -> list[RunLearningSummary]:
        return [RunLearningSummary(**item) for item in _read_json(self.run_summaries_path, {"run_summaries": []}).get("run_summaries", [])]

    def _save_run_summary(self, summary: RunLearningSummary) -> None:
        rows = [item for item in self._run_summaries() if item.run_summary_id != summary.run_summary_id]
        rows.append(summary)
        _write_json(self.run_summaries_path, {"run_summaries": [_dump(item) for item in rows]})

    def _candidates(self) -> list[MemoryCandidateV2]:
        return [MemoryCandidateV2(**item) for item in _read_json(self.candidates_path, {"candidates": []}).get("candidates", [])]

    def _save_candidate(self, candidate: MemoryCandidateV2) -> None:
        rows = [item for item in self._candidates() if item.candidate_id != candidate.candidate_id]
        rows.append(candidate)
        _write_json(self.candidates_path, {"candidates": [_dump(item) for item in rows]})

    def _memories(self) -> list[MemoryRecord]:
        return [MemoryRecord(**item) for item in _read_json(self.memories_path, {"memories": []}).get("memories", [])]

    def _save_memory(self, memory: MemoryRecord) -> None:
        rows = [item for item in self._memories() if item.memory_id != memory.memory_id]
        rows.append(memory)
        _write_json(self.memories_path, {"memories": [_dump(item) for item in rows]})

    def _project_profiles(self) -> dict[str, ProjectLearningProfile]:
        return {key: ProjectLearningProfile(**value) for key, value in _read_json(self.project_profiles_path, {"profiles": {}}).get("profiles", {}).items()}

    def _save_project_profile(self, profile: ProjectLearningProfile) -> None:
        rows = self._project_profiles()
        rows[profile.project_id] = profile
        _write_json(self.project_profiles_path, {"profiles": {key: _dump(value) for key, value in rows.items()}})

    def _skill_pack_profiles(self) -> dict[str, SkillPackLearningProfile]:
        return {key: SkillPackLearningProfile(**value) for key, value in _read_json(self.skill_pack_profiles_path, {"profiles": {}}).get("profiles", {}).items()}

    def _save_skill_pack_profile(self, profile: SkillPackLearningProfile) -> None:
        rows = self._skill_pack_profiles()
        rows[profile.skill_pack_id] = profile
        _write_json(self.skill_pack_profiles_path, {"profiles": {key: _dump(value) for key, value in rows.items()}})

    def _template_profiles(self) -> dict[str, TemplateLearningProfile]:
        return {key: TemplateLearningProfile(**value) for key, value in _read_json(self.template_profiles_path, {"profiles": {}}).get("profiles", {}).items()}

    def _save_template_profile(self, profile: TemplateLearningProfile) -> None:
        rows = self._template_profiles()
        rows[profile.template_id] = profile
        _write_json(self.template_profiles_path, {"profiles": {key: _dump(value) for key, value in rows.items()}})
