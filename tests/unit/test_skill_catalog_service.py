from aipinho.services.skills.skill_catalog_service import SkillCatalogService

def test_catalog_has_external_disabled_entries():
    skills=SkillCatalogService().catalog(); assert len(skills)==74; assert next(x for x in skills if x.skill_id=='imagegen').default_enabled is False
