from aipinho.schemas.skills.contracts import SkillInstallRequest
from aipinho.services.skills.skill_installer_service import SkillInstallerService

def test_installer_never_installs():
    request=SkillInstallRequest(manifest={'name':'x'},contract={'skill_id':'x'},dependencies=[]); assert SkillInstallerService().preview(request).installed is False
