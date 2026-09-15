from __future__ import annotations

from aipinho.services.runtime.runtime_operator_doctor_service import RuntimeOperatorDoctorService


def test_doctor_bounded_evidence_limits_large_collections_without_mutating_input() -> None:
    service = RuntimeOperatorDoctorService()
    value = [{"artifact_id": f"artifact_{index:08x}", "payload": "x" * 3000} for index in range(250)]

    bounded = service._bounded_evidence(value)

    assert len(value) == 250
    assert len(bounded) == 101
    assert bounded[-1]["_doctor_truncated_items"] == 150
    assert bounded[0]["payload"].endswith("<truncated>")


def test_doctor_scalar_list_matching_is_linear_membership() -> None:
    service = RuntimeOperatorDoctorService()
    actual = [f"artifact_{index:08x}" for index in range(5000)]
    expected = [actual[12], actual[4999]]

    assert service._matches_expected(actual, expected) is True
