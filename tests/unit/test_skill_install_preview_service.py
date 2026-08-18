from aipinho.schemas.skills.contracts import SkillInstallRequest
from aipinho.services.skills.skill_install_preview_service import SkillInstallPreviewService

def test_install_preview_blocks_invalid_contract():
    result=SkillInstallPreviewService().preview(SkillInstallRequest(manifest={'name':'x'},contract={'skill_id':'x'})); assert result.status=='blocked'; assert result.files_written is False
