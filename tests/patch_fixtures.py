from __future__ import annotations

import os
import shutil
from pathlib import Path

from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest


def patch_workspace(tmp_path: Path) -> Path:
    root = Path(os.environ.get("AIPINHO_TEST_MUTABLE_ROOT", r"C:\Users\rafae\Documents\AIpinhoTestes\.pytest"))
    workspace = root / tmp_path.name / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / "src").mkdir(parents=True)
    (workspace / "docs").mkdir()
    (workspace / "config" / "policies").mkdir(parents=True)
    (workspace / "src" / "app.py").write_text("print('old')\n", encoding="utf-8", newline="\n")
    (workspace / "docs" / "note.md").write_text("# Old\n", encoding="utf-8", newline="\n")
    return workspace


def patch_request(workspace: Path, path: str = "docs/note.md", objective: str = "Proponha um patch sem aplicar.") -> PatchPlanRequest:
    return PatchPlanRequest(
        workspace=str(workspace),
        objective=objective,
        affected_files=[path],
        evidence=[PatchEvidence(evidence_id="e1", source_type="user_request", source_path=path, excerpt="O usuário pediu proposta de patch sem aplicar.", confidence=0.7)],
        replacements={path: "# New"},
    )
