from __future__ import annotations

from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.rollback_note import RollbackNote


class RollbackNoteService:
    def build(self, files: list[AffectedFile]) -> list[RollbackNote]:
        return [
            RollbackNote(file_path=file.relative_path or file.path, original_hash=file.original_hash, summary="Manual rollback: restore this file content from the original hash/snapshot before applying any future patch.", steps=["Review diff preview.", "Use version control or stored original content to revert manually if a future apply sprint changes this file."])
            for file in files
            if file.status != "blocked"
        ]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rollback_note", "automatic_rollback_enabled": False}
