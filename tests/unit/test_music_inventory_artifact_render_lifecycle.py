from __future__ import annotations

import inspect

from aipinho.services.governance.runtime import readonly_analysis_artifact_runtime_service as runtime_module
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)


def test_music_inventory_event_mapping_does_not_emit_created_for_partial_or_blocked() -> None:
    source = inspect.getsource(ReadonlyAnalysisArtifactRuntimeService)

    assert '"ready": "artifact_created"' in source
    assert '"partial": "artifact_partial"' in source
    assert '"blocked": "artifact_blocked"' in source


def test_renderer_path_uses_governed_payloads_not_direct_filesystem_scan() -> None:
    source = inspect.getsource(runtime_module.ReadonlyAnalysisArtifactRuntimeService._contract_tabular_collection_content)

    assert "observed_entity_graph" in source
    assert "perception_payload" in source
    assert ".rglob(" not in source
    assert ".glob(" not in source
    assert "os.walk" not in source
