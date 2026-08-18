import pytest
from pydantic import ValidationError

from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService


def test_analysis_request_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        ProjectAnalysisRequest(workspace="x", unexpected=True)  # type: ignore[call-arg]


def test_project_analysis_result_contract_round_trips(tmp_path):
    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    result = ProjectAnalysisService().analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))
    dumped = result.model_dump()
    restored = ProjectAnalysisResult.model_validate(dumped)
    assert restored.result_id == result.result_id
    assert restored.report.status == result.report.status
