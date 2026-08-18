from aipinho.schemas.patching.quality import (
    DiffParseResult,
    PatchQualityFinding,
    PatchQualityGateRequest,
    PatchQualityGateResult,
    PatchQualityScore,
)


def test_patch_quality_contracts_validate():
    finding = PatchQualityFinding(finding_id="f1", category="syntax", message="x")
    score = PatchQualityScore(status="passed", score=100)
    request = PatchQualityGateRequest(diff_text="--- a/a\n+++ b/a\n@@ -1 +1 @@\n-a\n+b\n")
    result = PatchQualityGateResult(
        quality_id="patch_quality_abcdef",
        status="passed",
        score=score,
        diff_parse=DiffParseResult(status="ok", valid=True),
        findings=[finding],
        created_at="now",
        updated_at="now",
    )
    assert request.diff_text
    assert result.apply_enabled is False
    assert result.write_enabled is False
