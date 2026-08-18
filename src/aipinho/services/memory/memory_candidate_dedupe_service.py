from __future__ import annotations

import hashlib
import re

from aipinho.schemas.memory.memory_candidate import MemoryCandidateDedupe, MemoryCandidateScope


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


class MemoryCandidateDedupeService:
    def evaluate(self, text: str, *, kind: str, scope: MemoryCandidateScope, existing: list) -> MemoryCandidateDedupe:
        normalized = _normalize(text)
        normalized_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        kind_scope_hash = hashlib.sha256(f"{kind}|{scope.scope_type}|{scope.workspace}|{normalized}".encode("utf-8")).hexdigest()
        tokens = set(normalized.split())
        best_id = None
        best_similarity = 0.0
        for candidate in existing:
            if candidate.dedupe.normalized_hash == normalized_hash:
                return MemoryCandidateDedupe(status="duplicate", normalized_hash=normalized_hash, kind_scope_hash=kind_scope_hash, matched_candidate_id=candidate.candidate_id, similarity=1.0)
            other_tokens = set(_normalize(candidate.text).split())
            if not tokens or not other_tokens:
                continue
            similarity = len(tokens & other_tokens) / len(tokens | other_tokens)
            if candidate.kind == kind and candidate.scope.scope_type == scope.scope_type and similarity > best_similarity:
                best_similarity = similarity
                best_id = candidate.candidate_id
        if best_similarity >= 0.72:
            return MemoryCandidateDedupe(status="near_duplicate", normalized_hash=normalized_hash, kind_scope_hash=kind_scope_hash, matched_candidate_id=best_id, similarity=best_similarity)
        return MemoryCandidateDedupe(status="unique", normalized_hash=normalized_hash, kind_scope_hash=kind_scope_hash, similarity=best_similarity)
