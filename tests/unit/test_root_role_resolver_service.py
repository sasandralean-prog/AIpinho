from __future__ import annotations

from aipinho.services.semantics.root_role_resolver_service import RootRoleResolverService


class _NoModelReasoner:
    def propose_json(self, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("model reasoner should not be used for explicit authority")


class _CandidateReasoner:
    def __init__(self, *, role: str, confidence: float) -> None:
        self.role = role
        self.confidence = confidence

    def propose_json(self, **kwargs):
        return {
            "status": "candidate",
            "candidate": {
                "role": self.role,
                "confidence": self.confidence,
                "rationale": "semantic fixture",
                "evidence_refs": ["fixture:prompt"],
            },
            "model_id": "fixture-model",
            "response_id": "fixture-response",
            "real_inference": True,
            "evaluation_status": "accepted",
            "warnings": [],
        }


def test_explicit_root_role_is_authoritative_without_model_call() -> None:
    result = RootRoleResolverService(reasoner=_NoModelReasoner()).resolve(
        path="C:/project/media",
        prompt="Biblioteca: C:/project/media",
        explicit_role="library_root",
        allow_model_inference=True,
    )

    assert result.status == "resolved"
    assert result.role == "library_root"
    assert result.confidence == 1.0
    assert result.model_id is None
    assert result.provenance["candidate_source"] == "prompt_explicit_role"


def test_model_candidate_is_only_materialized_after_contract_validation() -> None:
    result = RootRoleResolverService(
        reasoner=_CandidateReasoner(role="corpus_root", confidence=0.83)
    ).resolve(
        path="D:/ambiguous",
        prompt="Use D:/ambiguous as the media collection.",
        allow_model_inference=True,
    )

    assert result.status == "resolved"
    assert result.role == "corpus_root"
    assert result.model_id == "fixture-model"
    assert result.deterministic_validation_status == "passed"
    assert result.provenance["authority"] == "deterministic_gate"


def test_low_confidence_model_candidate_fails_closed() -> None:
    result = RootRoleResolverService(
        reasoner=_CandidateReasoner(role="library_root", confidence=0.31)
    ).resolve(
        path="D:/ambiguous",
        prompt="Inspect D:/ambiguous.",
        allow_model_inference=True,
    )

    assert result.status == "ambiguous"
    assert result.role == "unknown_root"
    assert "ROOT_ROLE_CONFIDENCE_INSUFFICIENT" in result.reason_codes
