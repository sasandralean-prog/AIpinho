from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_transfer_api_creates_jobs_and_blocks_executable():
    c=TestClient(create_app()); assert c.post("/api/v1/transfers/downloads",json={"artifact_id":"a1"}).status_code==200; assert c.post("/api/v1/transfers/uploads",json={"filename":"bad.exe"}).status_code==409
