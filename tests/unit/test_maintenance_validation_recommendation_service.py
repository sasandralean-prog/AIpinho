import inspect
from aipinho.services.maintenance.maintenance_validation_recommendation_service import MaintenanceValidationRecommendationService

def test_validation_is_recommendation_not_shell_execution():
    source = inspect.getsource(MaintenanceValidationRecommendationService)
    assert "subprocess" not in source
    assert "execution_performed=True" not in source
