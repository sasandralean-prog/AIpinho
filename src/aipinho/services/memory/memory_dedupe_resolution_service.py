from __future__ import annotations


class MemoryDedupeResolutionService:
    def resolve(self, *, dedupe_status: str, resolution: str | None = None) -> dict[str, object]:
        if dedupe_status == "unique":
            return {"status": "resolved", "reason": "unique"}
        if dedupe_status == "duplicate" and resolution == "link_to_existing":
            return {"status": "linked", "reason": "link_to_existing"}
        if dedupe_status == "near_duplicate" and resolution in {"supersede_existing", "link_to_existing"}:
            return {"status": "resolved", "reason": resolution}
        return {"status": "blocked", "reason": f"dedupe_unresolved:{dedupe_status}"}
