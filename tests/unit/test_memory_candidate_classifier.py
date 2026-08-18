from aipinho.services.memory.memory_candidate_classifier import MemoryCandidateClassifier


def test_classifier_kinds():
    classifier = MemoryCandidateClassifier()
    assert classifier.classify("quality gate policy requires approval") == "policy_decision"
    assert classifier.classify("validation failed with missing evidence") == "validation_learning"
    assert classifier.classify("patch apply completed with rollback") == "patch_outcome"
    assert classifier.classify("known limitation exists") == "known_limitation"
    assert classifier.classify("risco de conflito") == "risk_pattern"
    assert classifier.classify("guarde isso") == "user_instruction"
