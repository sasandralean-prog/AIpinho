from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.services.patching.patch_test_recommendation_service import PatchTestRecommendationService


def test_patch_test_recommendation_service_suggests_without_execution():
    recs = PatchTestRecommendationService().recommend([AffectedFile(path="src/app.py", relative_path="src/app.py", status="allowed")])
    assert any(item.test_type == "py_compile" for item in recs)
    assert all(item.execution_enabled is False for item in recs)
