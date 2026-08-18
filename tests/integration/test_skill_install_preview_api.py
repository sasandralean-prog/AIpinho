from fastapi.testclient import TestClient
from aipinho.main import app
client=TestClient(app)

def test_install_preview_never_installs():
    body=client.post('/api/v1/skills/install/preview',json={'manifest':{'name':'x'},'contract':{'skill_id':'x'}}).json(); assert body['status']=='blocked'; assert body['files_written'] is False
