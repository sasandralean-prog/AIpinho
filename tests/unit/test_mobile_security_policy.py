from pathlib import Path
def test_mobile_has_no_token_or_dangerous_execution():
    text="\n".join(p.read_text(encoding="utf-8") for p in Path("apps/mobile/android/app/src/main/java").rglob("*.kt")); lower=text.lower(); assert "hardcoded_token" not in lower; assert "git push" not in lower; assert "apply_patch" not in lower; assert "run_shell" not in lower
