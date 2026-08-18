from aipinho.schemas.governance.lifecycle import CanonicalIntentDecision
from aipinho.schemas.runtime.runtime_doctor import ExpectedRuntimeContract
from aipinho.services.runtime.runtime_doctor_service import RuntimeDoctorService
from aipinho.services.semantic_runtime.semantic_ingress_doctor_service import SemanticIngressDoctorService


def test_semantic_ingress_doctor_records_prompt_normalization_and_state_effects() -> None:
    report = SemanticIngressDoctorService().analyze(
        "Sem modificar arquivos, gere relatorio de auditoria.",
        source_channel="unit",
    )

    assert report.status == "complete"
    assert report.prompt_normalization.normalized_text
    assert report.semantic_propositions
    assert {effect.target for effect in report.state_effects} >= {"workspace", "filesystem", "runtime", "knowledge"}
    assert report.intent_decision.selected_intent_id
    assert report.operation_contract_decision.selected_contract_type


def test_semantic_ingress_doctor_detects_encoding_degradation_without_changing_decision() -> None:
    report = SemanticIngressDoctorService().analyze(
        "NÃ£o modificar arquivos. Gerar relatorio.",
        source_channel="unit",
    )

    assert "ENCODING_MOJIBAKE_SUSPECTED" in report.reason_codes
    assert report.prompt_normalization.encoding_detected == "unicode_text_with_possible_mojibake"
    assert "latin1_to_utf8" in report.prompt_normalization.text_variants
    assert report.operation_contract_decision.decision_source == "governance_lifecycle"


def test_semantic_ingress_doctor_explains_readonly_to_mutation_mismatch() -> None:
    actual_intent = CanonicalIntentDecision(
        intent_type="patch_or_write_request",
        operation_type="patch_request",
        requires_task=True,
        readonly=False,
        source_channel="unit",
        evidence=["simulated_actual_decision"],
    )

    report = SemanticIngressDoctorService().analyze(
        "Sem modificar arquivos, gere relatorio de auditoria.",
        source_channel="unit",
        actual_intent=actual_intent,
        actual_operation_contract={"contract_type": "filesystem_write", "operation_type": "patch_request"},
    )

    assert "STATE_EFFECT_CONTRACT_MISMATCH" in report.reason_codes
    assert "READONLY_CONTRACT_PROMOTED_TO_MUTATION" in report.reason_codes
    assert report.operation_contract_decision.relation_to_state_effects == "conflict"


def test_runtime_doctor_classifies_semantic_ingress_reason_codes() -> None:
    ingress = SemanticIngressDoctorService().analyze(
        "NÃ£o modificar arquivos. Gerar relatorio.",
        source_channel="unit",
    ).model_dump(mode="json")

    report = RuntimeDoctorService().diagnose(
        expected=ExpectedRuntimeContract(),
        runtime={"governance_lifecycle": {"semantic_ingress_doctor": ingress}},
        create_artifacts=False,
    )

    assert report.matrix.encoding == "FAIL"
    assert any(finding.regression_type == "ENCODING_MOJIBAKE_SUSPECTED" for finding in report.findings)
