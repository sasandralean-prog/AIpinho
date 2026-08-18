from aipinho.schemas.skills.contracts import SkillInstallRequest
from aipinho.services.skills.skill_manifest_validator import SkillManifestValidator

def test_manifest_blocks_dependencies_and_download():
    result=SkillManifestValidator().validate(SkillInstallRequest(manifest={'name':'x'},contract={'skill_id':'x'},dependencies=['pkg'],source_uri='https://example.invalid')); assert 'dependency_install_blocked' in result['reasons']; assert 'external_download_blocked' in result['reasons']
