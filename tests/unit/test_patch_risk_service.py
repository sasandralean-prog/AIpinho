from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.services.patching.patch_risk_service import PatchRiskService


def test_patch_risk_service_levels():
    service = PatchRiskService()
    assert service.assess([AffectedFile(path="docs/a.md", status="allowed")], evidence_count=0).blocked
    assert service.assess([AffectedFile(path="config/x.yaml", status="allowed", risk_level="high")], evidence_count=1).risk_level == "high"
    assert service.assess([AffectedFile(path="docs/a.md", status="allowed", risk_level="low")], evidence_count=2).risk_level == "low"
