from pathlib import Path
def test_mobile_syncs_via_backend_only():
    text="\n".join(p.read_text(encoding="utf-8") for p in Path("apps/mobile/android/app/src/main/java").rglob("*.kt")); assert "launcher desktop" not in text.lower(); assert "/api/v1/sync/" in text
