from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.patch_evidence import PatchEvidence


class PatchEvidenceService:
    def normalize(self, evidence: list[PatchEvidence], *, user_request: str = "", affected_paths: list[str] | None = None) -> list[PatchEvidence]:
        if evidence:
            return evidence
        if user_request and affected_paths:
            return [
                PatchEvidence(
                    evidence_id=f"patch_evidence_{uuid4().hex}",
                    source_type="user_request",
                    source_path=affected_paths[0],
                    excerpt=user_request[:500],
                    confidence=0.5,
                    warnings=["user_request_as_supporting_evidence"],
                )
            ]
        return []

    def validate(self, evidence: list[PatchEvidence]) -> tuple[bool, list[str]]:
        if not evidence:
            return False, ["missing_evidence"]
        invalid = [item.evidence_id for item in evidence if not item.excerpt and item.line_start is None]
        return not invalid, ["invalid_evidence"] if invalid else []

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_evidence", "require_evidence": True}
