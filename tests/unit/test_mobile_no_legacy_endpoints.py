from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOBILE_SRC = ROOT / "apps" / "mobile" / "android" / "app" / "src" / "main" / "java"


def test_mobile_does_not_use_v2_endpoints() -> None:
    offenders: list[str] = []
    for path in MOBILE_SRC.rglob("*.kt"):
        text = path.read_text(encoding="utf-8")
        if "/v2" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_mobile_does_not_expose_forbidden_execution_surfaces() -> None:
    forbidden = ("git push", "apply_patch_direct", "/commands/run", "/files/write")
    offenders: list[str] = []
    for path in MOBILE_SRC.rglob("*.kt"):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
