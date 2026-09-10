from __future__ import annotations

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService


def _entity(**values: str) -> dict:
    return {
        "observed_attributes": {
            key: {"status": "observed", "value": value}
            for key, value in values.items()
        }
    }


def test_schema_coverage_preserves_alias_semantics_and_reports_bounded_projection() -> None:
    service = ObservedEntityCompilationService(
        policy={"attribute_aliases": {"name": ["name", "nome"], "size_bytes": ["size", "tamanho"]}}
    )

    result = service.schema_coverage(
        [_entity(name="alpha.txt", size_bytes="12")],
        ["nome", "tamanho", "missing"],
    )

    assert result["status"] == "partial"
    assert result["covered_fields"] == ["nome", "tamanho"]
    assert result["missing_fields"] == ["missing"]
    metrics = result["coverage_metrics"]
    assert metrics["lookup_strategy"] == "single_schema_projection"
    assert metrics["canonicalization_count"] == 3
    assert metrics["entity_field_checks"] == 3


def test_schema_coverage_does_not_canonicalize_once_per_entity_field(monkeypatch) -> None:
    service = ObservedEntityCompilationService(
        policy={"attribute_aliases": {"name": ["name"], "extension": ["extension"]}}
    )
    fields = ["name", "extension", "missing"]
    entities = [_entity(name=f"file-{index}.txt", extension="txt") for index in range(100)]
    calls = 0
    original = service.canonical_attribute_name

    def count_calls(field: str) -> str:
        nonlocal calls
        calls += 1
        return original(field)

    monkeypatch.setattr(service, "canonical_attribute_name", count_calls)
    result = service.schema_coverage(entities, fields)

    assert result["covered_fields"] == ["name", "extension"]
    assert result["missing_fields"] == ["missing"]
    assert calls == len(fields)
    assert result["coverage_metrics"]["entity_field_checks"] == len(entities) + 2


def test_schema_coverage_scales_by_entities_and_schema_not_alias_search_per_cell() -> None:
    service = ObservedEntityCompilationService(
        policy={"attribute_aliases": {"name": ["name"], "extension": ["extension"]}}
    )
    fields = ["name", "extension", "missing"]
    entities = [_entity(name=f"file-{index}.txt", extension="txt") for index in range(2500)]

    result = service.schema_coverage(entities, fields)

    assert result["coverage_metrics"]["canonicalization_count"] == len(fields)
    assert result["coverage_metrics"]["entity_field_checks"] <= len(fields) * len(entities)
    assert result["coverage_metrics"]["lookup_strategy"] == "single_schema_projection"
