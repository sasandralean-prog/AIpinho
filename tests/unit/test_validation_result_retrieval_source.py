from aipinho.schemas.validation.validation_finding import ValidationFinding
from aipinho.schemas.validation.validation_gate_result import ValidationGateResult
from aipinho.services.rag.sources.validation_result_retrieval_source import ValidationResultRetrievalSource
from aipinho.services.validation.validation_store import ValidationStore
from tests.unit.retrieval_test_helpers import request


def test_validation_result_source_returns_sanitized_cited_summary(tmp_path):
    store = ValidationStore(root=tmp_path)
    validation_id = "validation_" + "b" * 32
    store.save_result(
        ValidationGateResult(
            validation_id=validation_id,
            target_type="task_run",
            target_id="task_run_" + "a" * 32,
            status="passed",
            score=1.0,
            findings=[
                ValidationFinding(
                    finding_id="finding-1",
                    code="evidence_present",
                    title="Evidence present",
                    severity="info",
                    message="Required evidence was found.",
                    evidence=["source:1"],
                    validator="unit_test",
                )
            ],
        )
    )
    hits = ValidationResultRetrievalSource(store=store).retrieve(
        request(sources=["validation_results"], validation_id=validation_id)
    )
    assert len(hits) == 1
    assert hits[0].citation.citation_type == "validation_finding"
    assert hits[0].citation.evidence_id == "finding-1"
    assert hits[0].metadata["status"] == "passed"
