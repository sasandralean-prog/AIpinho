from __future__ import annotations

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)


def test_textual_phase_mentions_do_not_create_operational_dependencies() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    text = "Executar Fase 0/CVL antes da Fase 1 e depois comparar a calibração."

    dependencies = service._dependency_phase_ids(text, current_phase_id="phase_1")  # noqa: SLF001

    assert dependencies == []


def test_explicit_previous_phase_dependency_still_blocks_when_declared() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    text = "A Fase 2 depende dos artefatos anteriores e da Fase 1."

    dependencies = service._dependency_phase_ids(text, current_phase_id="phase_2")  # noqa: SLF001

    assert dependencies == ["phase_1"]
