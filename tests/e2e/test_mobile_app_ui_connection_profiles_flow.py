from pathlib import Path
from fastapi.testclient import TestClient
from aipinho.app_factory import create_app
def test_mobile_app_ui_connection_profiles_flow():
    root=Path("apps/mobile/android"); assert (root/"app/src/main/java/br/com/aipinho/mobile/MainActivity.kt").exists(); assert (root/"app/src/main/java/br/com/aipinho/mobile/ui/screens/PairingScreen.kt").exists(); c=TestClient(create_app()); assert c.get("/api/v1/mobile/status").status_code==200
