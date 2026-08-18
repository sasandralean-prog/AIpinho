from __future__ import annotations

from aipinho.schemas.memory.memory_candidate import MemoryCandidateConflict, MemoryCandidateScope


class MemoryCandidateConflictService:
    PAIRS = (("enabled", "disabled"), ("allowed", "blocked"), ("passed", "failed"), ("usa ", "nao usa "), ("usa ", "não usa "))

    def evaluate(self, text: str, *, kind: str, scope: MemoryCandidateScope, existing: list) -> MemoryCandidateConflict:
        lowered = text.lower()
        conflicts: list[str] = []
        reasons: list[str] = []
        for candidate in existing:
            if candidate.kind != kind or candidate.scope.scope_type != scope.scope_type:
                continue
            other = candidate.text.lower()
            for left, right in self.PAIRS:
                if (left in lowered and right in other) or (right in lowered and left in other):
                    conflicts.append(candidate.candidate_id)
                    reasons.append(f"contradiction:{left}/{right}")
                    break
        return MemoryCandidateConflict(has_conflict=bool(conflicts), conflict_candidate_ids=list(dict.fromkeys(conflicts)), reasons=list(dict.fromkeys(reasons)))
