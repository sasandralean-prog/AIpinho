from aipinho.services.prompt_intelligence.ambiguity_detector import AmbiguityDetector
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatcher


def test_aliases_are_grouped_by_type():
    matcher = ConceptMatcher().load()
    matches = matcher.match("O que voce consegue fazer?")

    assert matcher.has_type(matches, "actor")
    assert matcher.has_type(matches, "object")
    assert any(match.concept_id == "capability_object" for match in matches)


def test_consegue_fazer_is_not_mutation():
    matcher = ConceptMatcher().load()
    matches = matcher.match("O que voce consegue fazer?")

    assert not matcher.has_type(matches, "operation_mutation")


def test_architecture_is_object_not_operation():
    matcher = ConceptMatcher().load()
    matches = matcher.match("Explique sua arquitetura atual")

    assert any(match.concept_id == "architecture_object" for match in matches)
    assert not any(match.alias == "arquitetura" and match.concept_type.startswith("operation") for match in matches)


def test_ambiguity_light_is_contextual():
    matcher = ConceptMatcher().load()
    detector = AmbiguityDetector(concept_matcher=matcher).load()
    casual = matcher.match("Bom dia, tudo certo?")
    operational = matcher.match("Arrume tudo")

    assert detector.detect("Bom dia, tudo certo?", casual, workspace_requires_clarification=False, confidence=0.7, is_operational=False).is_ambiguous is False
    assert detector.detect("Arrume tudo", operational, workspace_requires_clarification=True, confidence=0.7, is_operational=True).is_ambiguous is True


def test_aliases_do_not_match_inside_unrelated_words():
    matcher = ConceptMatcher().load()
    matches = matcher.match("Teste controlado com permissoes necessarias e proposta de sprint.")

    matched_aliases = {match.normalized_alias for match in matches}

    assert "ola" not in matched_aliases
    assert "isso" not in matched_aliases
    assert "print" not in matched_aliases
