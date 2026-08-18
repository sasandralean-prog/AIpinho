from __future__ import annotations

from aipinho.services.artifacts.row_level_semantic_validation_service import RowLevelSemanticValidationService


def test_music_inventory_schema_aliases_are_normalized_before_missing_columns() -> None:
    content = "entity_id,tamanho,canais,observa_es,evidence_ref\nentity_1,10,2,limited,evidence:1\n"

    summary = RowLevelSemanticValidationService().summarize_csv(
        content=content,
        declared_columns=["entity_id", "size_bytes", "channels", "observations", "evidence_ref"],
        required_columns=["entity_id", "size_bytes", "channels", "observations", "evidence_ref"],
    ).model_dump(mode="json")

    coverage = summary["column_coverage"]
    assert coverage["missing_columns"] == []
    assert coverage["status"] == "satisfied"
