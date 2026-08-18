from __future__ import annotations

from aipinho.core.dependency_container import DependencyContainer, build_container


def bootstrap() -> DependencyContainer:
    return build_container()
