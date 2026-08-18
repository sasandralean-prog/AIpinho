from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from tests.unit.rag_memory_test_helpers import ready_plan


def test_valid_output_citation_is_accepted(tmp_path):
    plan = ready_plan(tmp_path)
    citation_id = next(iter(plan.citation_map.citations))
    result = ContextUsageValidator().validate_output(f"Resultado citado {citation_id}.", plan)
    assert result.valid is True


def test_fabricated_citation_is_rejected(tmp_path):
    plan = ready_plan(tmp_path)
    result = ContextUsageValidator().validate_output("Use citation_fake_01.", plan)
    assert result.valid is False
    assert "fabricated_citation:citation_fake_01" in result.violations


def test_unsupported_file_reference_is_rejected(tmp_path):
    plan = ready_plan(tmp_path)
    citation_id = next(iter(plan.citation_map.citations))
    result = ContextUsageValidator().validate_output(f"Veja src/unknown.py {citation_id}.", plan)
    assert result.valid is False
    assert any(item.startswith("unsupported_file_reference") for item in result.violations)


def test_uncited_contextual_output_warns(tmp_path):
    plan = ready_plan(tmp_path)
    result = ContextUsageValidator().validate_output("Resposta baseada no contexto.", plan)
    assert result.valid is True
    assert "contextual_output_without_citation" in result.warnings
