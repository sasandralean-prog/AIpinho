from fastapi.testclient import TestClient
from aipinho.main import app
client=TestClient(app)

def test_governed_tools_api():
    catalog=client.get('/api/v1/tools/catalog'); assert catalog.status_code==200; assert catalog.json()['count']==29
    shell=client.get('/api/v1/tools/shell.powershell').json()['tool']; assert shell['default_enabled'] is False
    preview=client.post('/api/v1/tools/invocation/preview',json={'tool_id':'shell.powershell','input':{'command':'echo hi'}}).json(); assert preview['status']=='blocked'; assert preview['executed'] is False
