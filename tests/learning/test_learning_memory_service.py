from __future__ import annotations

import json
from pathlib import Path

from aipinho.schemas.memory.learning import LearningExtractionRequest, MemoryQuery
from aipinho.services.memory.learning_memory_service import LearningMemoryService

ROOT = Path(__file__).resolve().parents[2]


def _fixture(name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "learning" / name).read_text(encoding="utf-8"))


def _service(tmp_path: Path) -> LearningMemoryService:
    return LearningMemoryService(root=tmp_path / "learning")


def test_extract_valid_run_creates_candidates_and_profiles(tmp_path: Path) -> None:
    service = _service(tmp_path)

    result = service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))

    assert result.status == "candidates_created"
    assert result.candidates
    assert all(candidate.evidence_refs for candidate in result.candidates)
    assert service.project_profile("project_fixture").candidate_ids
    assert service.skill_pack_profile("debug_pack").candidate_ids


def test_accept_candidate_creates_curated_learning_memory(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))
    candidate_id = result.candidates[0].candidate_id

    accepted = service.accept_candidate(candidate_id, reviewed_by="tester", reason="validated fixture")
    query = service.query(MemoryQuery(project_id="project_fixture", type=result.candidates[0].type))

    assert accepted["status"] == "accepted"
    assert accepted["memory"].evidence_refs
    assert query["total"] >= 1
    assert service.project_profile("project_fixture").accepted_memory_ids


def test_raw_log_payload_is_blocked_and_not_accepted(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.extract(LearningExtractionRequest(**_fixture("raw_log_blocked.json")))

    assert result.status == "blocked"
    assert "raw_or_stacktrace_payload_blocked" in result.blocked_reason_codes
    accepted = service.accept_candidate(result.candidates[0].candidate_id)
    assert accepted["status"] == "blocked"
    assert "raw_log_not_accepted" in accepted["blocked_reason_codes"]


def test_secret_payload_is_blocked_and_redacted(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.extract(LearningExtractionRequest(**_fixture("secret_blocked.json")))

    assert result.status == "blocked"
    assert "secret_detected" in result.blocked_reason_codes
    candidate = result.candidates[0]
    assert candidate.contains_secret_risk is True
    assert "fake-token-value" not in json.dumps(candidate.model_dump())


def test_missing_evidence_blocks_learning_memory(tmp_path: Path) -> None:
    service = _service(tmp_path)
    payload = _fixture("valid_run_learning.json")
    payload["evidence_refs"] = []

    result = service.extract(LearningExtractionRequest(**payload))

    assert result.status == "blocked"
    assert "learning_evidence_required" in result.blocked_reason_codes


def test_duplicate_candidate_is_superseded(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))
    second = service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))

    assert first.candidates[0].status == "proposed"
    assert any(candidate.status == "superseded" for candidate in second.candidates)


def test_review_lifecycle_reject_archive_stale(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))
    ids = [candidate.candidate_id for candidate in result.candidates[:3]]

    rejected = service.reject_candidate(ids[0], reason="not reusable")
    archived = service.archive_candidate(ids[1], reason="historic only")
    stale = service.mark_stale(ids[2], reason="outdated")

    assert rejected.status == "rejected"
    assert archived.status == "archived"
    assert stale.status == "stale"


def test_mobile_view_models_hide_raw_by_default(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.extract(LearningExtractionRequest(**_fixture("valid_run_learning.json")))

    memory = service.mobile_memory_view_model()
    learning = service.mobile_learning_view_model()

    assert memory["state"]["raw_default_visible"] is False
    assert learning["state"]["raw_default_visible"] is False
    assert memory["review_queue"]
    assert learning["run_summaries"]
