from pathlib import Path


def test_launcher_ui_does_not_import_backend_services_for_state() -> None:
    root = Path("apps/launcher/ui")
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "aipinho.services" in text:
            offenders.append(str(path))
    assert offenders == []


def test_launcher_ui_has_no_shell_git_or_patch_apply_buttons() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("apps/launcher/ui").rglob("*.py"))
    assert "git push" not in text
    assert "shell" not in text.lower()
    assert "apply patch" not in text.lower()
