from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.services.patching.rollback_note_service import RollbackNoteService


def test_rollback_note_service_conceptual_only():
    notes = RollbackNoteService().build([AffectedFile(path="docs/a.md", relative_path="docs/a.md", status="allowed", original_hash="h")])
    assert notes[0].automatic_rollback_enabled is False
    assert notes[0].original_hash == "h"
