from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import UnsafePathError


def resolve_within_root(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafePathError(f"Path escapes allowed root: {resolved_path}") from exc
    return resolved_path
