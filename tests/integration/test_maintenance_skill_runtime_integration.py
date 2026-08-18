from fastapi.testclient import TestClient
from aipinho.main import app
client = TestClient(app)

def test_maintenance_skills_are_valid_preview_contracts():
    body=client.get("/api/v1/skills/catalog").json()
    values=[item for item in body["skills"] if item["category"]=="maintenance"]
    assert len(values)==7
    assert all(item["supports_real_execution"] is False for item in values)
    assert {item["execution_mode"] for item in values} <= {"read_only","preview_only","candidate_only"}
