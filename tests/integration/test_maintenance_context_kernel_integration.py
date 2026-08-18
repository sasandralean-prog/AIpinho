from fastapi.testclient import TestClient
from aipinho.main import app
from tests.maintenance_helpers import create_diagnosis
client = TestClient(app)

def test_diagnosis_uses_maintenance_context_purpose_and_trace():
    run = create_diagnosis(client)
    diagnosis=run["diagnosis"]
    assert diagnosis["context_bundle_id"].startswith("bundle_")
    assert diagnosis["context_trace_id"].startswith("context_trace_")
