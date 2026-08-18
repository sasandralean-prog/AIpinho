from aipinho.services.memory.memory_candidate_extractor import MemoryCandidateExtractor


def test_extract_from_report_payload():
    source, requests = MemoryCandidateExtractor().extract(source_type="project_report", payload={"workspace": "C:\\Dev\\AIpinho", "findings": [{"summary": "Policy kernel must own permissions."}]})
    assert source.source_type == "project_report"
    assert requests[0].kind == "architecture_decision"
    assert requests[0].evidence


def test_extract_from_task_result_partial():
    _, requests = MemoryCandidateExtractor().extract(source_type="task_run_result", payload={"status": "partial", "limitations": ["Validation did not run."]})
    assert any(item.kind == "known_limitation" for item in requests)


def test_extract_from_validation_failed():
    _, requests = MemoryCandidateExtractor().extract(source_type="validation_result", payload={"status": "failed", "findings": [{"message": "Missing evidence."}]})
    assert requests[0].kind == "validation_learning"


def test_extract_from_patch_apply_completed():
    _, requests = MemoryCandidateExtractor().extract(source_type="patch_apply_result", payload={"status": "completed", "post_apply_validation": {"passed": True}})
    assert requests[0].kind == "patch_outcome"


def test_extract_limits_candidates():
    findings = [{"summary": f"Finding {i}"} for i in range(50)]
    _, requests = MemoryCandidateExtractor().extract(source_type="project_report", payload={"workspace": "C:\\Dev\\AIpinho", "findings": findings})
    assert len(requests) == 20
