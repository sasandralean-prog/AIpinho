from __future__ import annotations

from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.test_recommendation import TestRecommendation


class PatchTestRecommendationService:
    def recommend(self, files: list[AffectedFile]) -> list[TestRecommendation]:
        recommendations: list[TestRecommendation] = []
        if any((file.relative_path or file.path).endswith(".py") for file in files):
            recommendations.append(TestRecommendation(test_type="py_compile", command="python -m py_compile <affected python files>", reason="Python preview should be syntax-checked before any future apply.", execution_enabled=False))
            recommendations.append(TestRecommendation(test_type="unit", command="python -m pytest tests/unit -q", reason="Run focused unit tests in a future validation step.", execution_enabled=False))
        if any("/api/" in (file.relative_path or file.path).replace("\\", "/") for file in files):
            recommendations.append(TestRecommendation(test_type="integration", command="python -m pytest tests/integration -q", reason="API changes need integration coverage before future apply.", execution_enabled=False))
        if not recommendations:
            recommendations.append(TestRecommendation(test_type="review", command="manual review", reason="Review diff preview and evidence before any future apply.", execution_enabled=False))
        return recommendations

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_test_recommendation", "run_tests_enabled": False}
