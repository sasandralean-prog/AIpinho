from pathlib import Path

def test_launcher_has_no_dangerous_common_buttons():
    text="\n".join(p.read_text(encoding="utf-8") for p in Path("apps/launcher/ui").rglob("*.py"))
    lowered=text.lower()
    assert "git push" not in lowered
    assert "apply patch" not in lowered
    assert "run_shell" not in lowered
