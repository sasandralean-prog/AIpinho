from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from aipinho.schemas.semantic_runtime.mission_completion_requirements import (
    MissionCompletionRequirementEvidence,
    MissionCompletionRequirementResolution,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)


class MissionCompletionRequirementIngressService:
    """Extract explicit mission success/validation requirements as proposals.

    The model may identify semantic requirements, but deterministic code
    validates evidence excerpts against the supplied prompt before any
    requirement reaches MissionContract.
    """

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        max_segment_chars: int = 1600,
        segment_overlap_chars: int = 120,
        max_reasoner_calls: int = 8,
        max_requirements: int = 32,
        max_requirements_per_segment: int = 6,
        max_output_tokens: int = 384,
    ) -> None:
        self.reasoner = reasoner or ContractBoundSemanticReasoner()
        self.max_segment_chars = max(1200, int(max_segment_chars))
        self.segment_overlap_chars = max(
            0,
            min(int(segment_overlap_chars), self.max_segment_chars // 3),
        )
        self.max_reasoner_calls = max(1, int(max_reasoner_calls))
        self.max_requirements = max(1, int(max_requirements))
        self.max_requirements_per_segment = max(
            1,
            int(max_requirements_per_segment),
        )
        self.max_output_tokens = max(1, int(max_output_tokens))

    def resolve(
        self,
        *,
        prompt: str,
        enabled: bool,
    ) -> MissionCompletionRequirementResolution:
        if not enabled:
            return MissionCompletionRequirementResolution(
                status="not_applicable",
                reason_code="MISSION_COMPLETION_REQUIREMENT_INGRESS_NOT_APPLICABLE",
            )
        text = str(prompt or "")
        if not text.strip():
            return MissionCompletionRequirementResolution(
                status="resolved",
                reason_code="MISSION_COMPLETION_REQUIREMENTS_NONE_EXPLICIT",
            )

        segments = self._segments(text)
        if len(segments) > self.max_reasoner_calls:
            return MissionCompletionRequirementResolution(
                status="unavailable",
                reason_code="MISSION_COMPLETION_REQUIREMENT_CALL_LIMIT_EXCEEDED",
                provenance={
                    "required_reasoner_calls": len(segments),
                    "max_reasoner_calls": self.max_reasoner_calls,
                },
            )

        terminal_ids = self._terminal_success_evidence_ids(segments)
        semantic_goal = (
            "Extract only explicit mission completion criteria and explicit "
            "validation requirements from supplied prompt evidence units. "
            "Each proposed requirement must select one exact evidence_id from "
            "the supplied units. Do not copy, translate, paraphrase, or invent "
            "evidence, permissions, authority, or success."
        )
        rules = [
            (
                "Return only clauses that explicitly define mission success, "
                "a required final deliverable/state, or a required validation "
                "needed before success may be claimed."
            ),
            (
                "Prioritize terminal success conditions: clauses that explicitly "
                "state when the mission/task is considered complete, successful, "
                "accepted, or valid. Process steps, suggested commands, commit "
                "message examples, and report fields are lower priority unless "
                "the prompt explicitly makes mission success depend on them."
            ),
            (
                "Do not extract ordinary implementation instructions unless "
                "the text explicitly makes them part of success or validation."
            ),
            (
                "When one evidence unit states an all-of success condition with "
                "multiple required outcomes, emit one separate requirement row "
                "for each distinct required outcome using the same evidence_id."
            ),
            (
                "kind must be completion for required end-state/deliverable "
                "criteria or validation for checks/evidence required before "
                "success."
            ),
            (
                "requirement must be a concise lower_snake_case semantic key; "
                "do not include file paths, secrets, or prose in the key."
            ),
            (
                "evidence_id must exactly match one supplied evidence unit id. "
                "Do not copy or rewrite evidence text."
            ),
            (
                "If this segment has no explicit completion or validation "
                "criterion, return an empty requirements list."
            ),
            f"Return at most {self.max_requirements_per_segment} requirements.",
        ]
        output_schema = {
            "requirements": [
                {
                    "kind": "completion|validation",
                    "requirement": "lower_snake_case_key",
                    "evidence_id": "exact supplied evidence unit id",
                }
            ]
        }

        accepted: list[MissionCompletionRequirementEvidence] = []
        batch_provenance: list[dict[str, Any]] = []
        warnings: list[str] = []
        for index, segment in enumerate(segments):
            evidence_units = self._evidence_units(segment, index)
            evidence_by_id = {
                item["evidence_id"]: item["text"]
                for item in evidence_units
            }
            if terminal_ids:
                evidence_units = [
                    item for item in evidence_units
                    if item["evidence_id"] in terminal_ids
                ]
                evidence_by_id = {
                    item["evidence_id"]: item["text"]
                    for item in evidence_units
                }
                if not evidence_units:
                    continue
            active_rules = rules
            if terminal_ids:
                active_rules = [
                    (
                        "Every supplied evidence unit is an explicit terminal "
                        "mission-success criterion selected deterministically."
                    ),
                    (
                        "Decompose every distinct required outcome in each "
                        "supplied all-of criterion; do not return an empty list."
                    ),
                    (
                        "kind=completion for required final artifact/state/action "
                        "outcomes; kind=validation for outcomes whose wording "
                        "requires validation, testing, verification, demonstration, "
                        "proof, checking, or evidence before success."
                    ),
                    (
                        "requirement must be a concise lower_snake_case semantic "
                        "key grounded only in the supplied evidence."
                    ),
                    "Use the exact supplied evidence_id for every row.",
                    f"Return at most {self.max_requirements_per_segment} requirements.",
                ]
            payload = {
                "segment_index": index,
                "evidence_units": evidence_units,
                "rules": active_rules,
                "output_schema": output_schema,
            }
            response = self.reasoner.propose_json(
                semantic_goal=semantic_goal,
                payload=payload,
                allowed_fields=["requirements"],
                required_fields=["requirements"],
                role_id="mission_completion_requirement_extractor",
                max_tokens=self.max_output_tokens,
            )
            response_warnings = [
                str(item)
                for item in list(response.get("warnings") or [])
                if str(item)
            ]
            warnings.extend(response_warnings)
            batch_provenance.append(
                {
                    "segment_index": index,
                    "segment_chars": len(segment),
                    "model_id": response.get("model_id"),
                    "response_id": response.get("response_id"),
                    "real_inference": response.get("real_inference"),
                    "evaluation_status": response.get("evaluation_status"),
                    "retry_attempts": response.get("retry_attempts"),
                    "warnings": response_warnings,
                }
            )
            if response.get("status") != "candidate":
                return MissionCompletionRequirementResolution(
                    status="unavailable",
                    reason_code=str(
                        response.get("reason_code")
                        or "MISSION_COMPLETION_REQUIREMENT_REASONER_UNAVAILABLE"
                    ),
                    provenance=self._provenance(
                        batch_provenance,
                        warnings,
                    ),
                )
            candidate = response.get("candidate")
            rows = (
                candidate.get("requirements")
                if isinstance(candidate, dict)
                else None
            )
            if not isinstance(rows, list):
                return MissionCompletionRequirementResolution(
                    status="invalid",
                    reason_code="MISSION_COMPLETION_REQUIREMENTS_LIST_REQUIRED",
                    provenance=self._provenance(
                        batch_provenance,
                        warnings,
                    ),
                )
            if len(rows) > self.max_requirements_per_segment:
                return MissionCompletionRequirementResolution(
                    status="invalid",
                    reason_code="MISSION_COMPLETION_REQUIREMENT_SEGMENT_LIMIT_EXCEEDED",
                    provenance=self._provenance(
                        batch_provenance,
                        warnings,
                    ),
                )

            if terminal_ids and not rows:
                return MissionCompletionRequirementResolution(
                    status="invalid",
                    reason_code=(
                        "MISSION_COMPLETION_TERMINAL_CRITERION_NOT_DECOMPOSED"
                    ),
                    provenance=self._provenance(
                        batch_provenance,
                        warnings,
                    ),
                )

            for row in rows:
                if not isinstance(row, dict):
                    return MissionCompletionRequirementResolution(
                        status="invalid",
                        reason_code="MISSION_COMPLETION_REQUIREMENT_CANDIDATE_INVALID",
                        provenance=self._provenance(
                            batch_provenance,
                            warnings,
                        ),
                    )
                kind = str(row.get("kind") or "").strip().casefold()
                evidence_id = str(
                    row.get("evidence_id") or ""
                ).strip()
                excerpt = str(
                    evidence_by_id.get(evidence_id) or ""
                ).strip()
                requirement = self._requirement_key(
                    str(row.get("requirement") or "")
                )
                try:
                    confidence = float(row.get("confidence", 1.0))
                except (TypeError, ValueError):
                    confidence = 0.0
                if kind not in {"completion", "validation"}:
                    return MissionCompletionRequirementResolution(
                        status="invalid",
                        reason_code="MISSION_COMPLETION_REQUIREMENT_KIND_INVALID",
                        provenance=self._provenance(
                            batch_provenance,
                            warnings,
                        ),
                    )
                if not requirement:
                    return MissionCompletionRequirementResolution(
                        status="invalid",
                        reason_code="MISSION_COMPLETION_REQUIREMENT_CANDIDATE_INVALID",
                        provenance=self._provenance(
                            batch_provenance,
                            warnings,
                        ),
                    )
                if (
                    not evidence_id
                    or evidence_id not in evidence_by_id
                    or not excerpt
                ):
                    return MissionCompletionRequirementResolution(
                        status="invalid",
                        reason_code=(
                            "MISSION_COMPLETION_REQUIREMENT_EVIDENCE_NOT_IN_PROMPT"
                        ),
                        provenance=self._provenance(
                            batch_provenance,
                            warnings,
                        ),
                    )
                if excerpt not in segment:
                    return MissionCompletionRequirementResolution(
                        status="invalid",
                        reason_code=(
                            "MISSION_COMPLETION_REQUIREMENT_EVIDENCE_NOT_IN_PROMPT"
                        ),
                        provenance=self._provenance(
                            batch_provenance,
                            warnings,
                        ),
                    )
                if confidence < 0.65:
                    warnings.append(
                        "mission_completion_requirement_low_confidence_omitted"
                    )
                    continue
                accepted.append(
                    MissionCompletionRequirementEvidence(
                        kind=kind,  # type: ignore[arg-type]
                        requirement=requirement,
                        evidence_excerpt=excerpt,
                        confidence=min(1.0, max(0.0, confidence)),
                        rationale=str(row.get("rationale") or "").strip(),
                        segment_index=index,
                    )
                )

        evidence = self._dedupe(accepted)
        if len(evidence) > self.max_requirements:
            return MissionCompletionRequirementResolution(
                status="unavailable",
                reason_code="MISSION_COMPLETION_REQUIREMENT_TOTAL_LIMIT_EXCEEDED",
                provenance=self._provenance(
                    batch_provenance,
                    warnings,
                ),
            )
        completion = self._unique(
            [
                item.requirement
                for item in evidence
                if item.kind == "completion"
            ]
        )
        validation = self._unique(
            [
                item.requirement
                for item in evidence
                if item.kind == "validation"
            ]
        )
        reason_code = (
            "MISSION_COMPLETION_REQUIREMENTS_RESOLVED"
            if evidence
            else "MISSION_COMPLETION_REQUIREMENTS_NONE_EXPLICIT"
        )
        provenance = self._provenance(
            batch_provenance,
            warnings,
        )
        provenance["evidence_refs"] = [
            self._evidence_ref(item)
            for item in evidence
        ]
        return MissionCompletionRequirementResolution(
            status="resolved",
            reason_code=reason_code,
            completion_requirements=completion,
            validation_requirements=validation,
            allow_limited_completion=False,
            evidence=evidence,
            provenance=provenance,
        )

    def _terminal_success_evidence_ids(
        self,
        segments: list[str],
    ) -> set[str]:
        ids: set[str] = set()
        markers = (
            "criterio de sucesso",
            "success criterion",
            "success criteria",
            "definition of done",
            "done criterion",
            "completion criterion",
            "completion criteria",
            "acceptance criterion",
            "acceptance criteria",
        )
        for index, segment in enumerate(segments):
            for item in self._evidence_units(segment, index):
                normalized = self._normalized_evidence(item["text"])
                ascii_text = "".join(
                    char
                    for char in unicodedata.normalize("NFKD", normalized)
                    if not unicodedata.combining(char)
                )
                if any(marker in ascii_text for marker in markers):
                    ids.add(item["evidence_id"])
        return ids

    def _segments(self, text: str) -> list[str]:
        if len(text) <= self.max_segment_chars:
            return [text]
        segments: list[str] = []
        start = 0
        total = len(text)
        while start < total:
            end = min(total, start + self.max_segment_chars)
            if end < total:
                floor = start + int(self.max_segment_chars * 0.65)
                boundary = max(
                    text.rfind("\n", floor, end),
                    text.rfind(" ", floor, end),
                )
                if boundary > start:
                    end = boundary
            segment = text[start:end]
            if segment:
                segments.append(segment)
            if end >= total:
                break
            next_start = max(start + 1, end - self.segment_overlap_chars)
            start = next_start
        return segments

    @staticmethod
    def _evidence_units(
        segment: str,
        segment_index: int,
    ) -> list[dict[str, str]]:
        raw_parts = re.split(
            r"(?:\r?\n)+|(?<=[.!?;])\s+",
            str(segment),
        )
        units: list[dict[str, str]] = []
        for raw in raw_parts:
            text = raw.strip()
            if not text:
                continue
            chunks: list[str] = []
            start = 0
            while start < len(text):
                end = min(len(text), start + 1200)
                if end < len(text):
                    boundary = text.rfind(" ", start, end)
                    if boundary > start + 600:
                        end = boundary
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = max(end, start + 1)
            for chunk in chunks:
                units.append(
                    {
                        "evidence_id": (
                            f"segment_{segment_index}_evidence_{len(units)}"
                        ),
                        "text": chunk,
                    }
                )
        return units

    @staticmethod
    def _normalized_evidence(value: str) -> str:
        return " ".join(str(value).casefold().split())

    @staticmethod
    def _requirement_key(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value))
        ascii_value = "".join(
            char
            for char in normalized
            if not unicodedata.combining(char)
        )
        key = re.sub(
            r"[^a-z0-9]+",
            "_",
            ascii_value.casefold(),
        ).strip("_")
        if not key or not key[0].isalpha():
            return ""
        return key[:64].rstrip("_")

    def _dedupe(
        self,
        items: list[MissionCompletionRequirementEvidence],
    ) -> list[MissionCompletionRequirementEvidence]:
        unique: dict[
            tuple[str, str, str],
            MissionCompletionRequirementEvidence,
        ] = {}
        for item in items:
            key = (
                item.kind,
                item.requirement,
                self._normalized_evidence(item.evidence_excerpt),
            )
            previous = unique.get(key)
            if previous is None or item.confidence > previous.confidence:
                unique[key] = item
        return list(unique.values())

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(str(item) for item in values if str(item))
        )

    @staticmethod
    def _evidence_ref(
        item: MissionCompletionRequirementEvidence,
    ) -> str:
        payload = (
            f"{item.kind}|{item.requirement}|{item.evidence_excerpt}"
        )
        digest = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:24]
        return f"mission_completion_requirement:{digest}"

    @staticmethod
    def _provenance(
        batches: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        model_ids = list(
            dict.fromkeys(
                str(item.get("model_id"))
                for item in batches
                if item.get("model_id")
            )
        )
        return {
            "role_id": "mission_completion_requirement_extractor",
            "reasoner_calls": len(batches),
            "model_ids": model_ids,
            "real_inference": (
                all(
                    bool(item.get("real_inference"))
                    for item in batches
                    if item.get("real_inference") is not None
                )
                if batches
                else None
            ),
            "evaluation_statuses": [
                item.get("evaluation_status")
                for item in batches
                if item.get("evaluation_status")
            ],
            "warnings": list(
                dict.fromkeys(
                    str(item) for item in warnings if str(item)
                )
            ),
            "batches": batches,
        }
