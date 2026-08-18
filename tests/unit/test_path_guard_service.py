from aipinho.services.security.path_guard_service import PathGuardService


def test_path_guard_allows_normal_path_inside_workspace(tmp_path):
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    decision = PathGuardService().validate_read_target(str(tmp_path), "README.md")
    assert decision.allowed is True
    assert decision.status == "allowed"


def test_path_guard_blocks_traversal(tmp_path):
    decision = PathGuardService().validate_read_target(str(tmp_path), r"..\outside.txt")
    assert decision.allowed is False
    assert "path_traversal" in decision.violations


def test_path_guard_blocks_absolute_outside_workspace(tmp_path):
    decision = PathGuardService().validate_read_target(str(tmp_path), r"C:\Users\rafae\.ssh\id_rsa")
    assert decision.allowed is False
    assert "outside_workspace" in decision.violations


def test_path_guard_blocks_protected_root():
    decision = PathGuardService().validate_read_target(r"C:\PinhoabacaxiAI", ".")
    assert decision.allowed is False
    assert "protected_root" in decision.violations


def test_path_guard_blocks_secret_and_blocked_extension(tmp_path):
    secret = PathGuardService().validate_read_target(str(tmp_path), ".env")
    binary = PathGuardService().validate_read_target(str(tmp_path), "archive.zip")
    assert "secret_file" in secret.violations
    assert "blocked_extension" in binary.violations
