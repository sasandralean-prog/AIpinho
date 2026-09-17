from __future__ import annotations

import os
from pathlib import Path

from aipinho.schemas.runtime.mission_contract import MissionResourceScope


class MissionLocalResourceScopeService:
    """Path matcher for already-frozen local mission resources."""

    def scope_for_path(
        self,
        resources: list[MissionResourceScope] | None,
        path: str | None,
    ) -> MissionResourceScope | None:
        if not path:
            return None
        candidates = [
            resource
            for resource in (resources or [])
            if resource.resource_type == "local_workspace"
            and resource.locator
            and self.is_under(path, resource.locator)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: len(self.normalize(item.locator or "")))

    def resource_by_id(
        self,
        resources: list[MissionResourceScope] | None,
        resource_id: str | None,
    ) -> MissionResourceScope | None:
        if not resource_id:
            return None
        return next(
            (
                resource
                for resource in (resources or [])
                if resource.resource_type == "local_workspace"
                and resource.resource_id == resource_id
            ),
            None,
        )

    def normalize(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def is_under(self, path: str, root: str) -> bool:
        normalized_path = self.normalize(path)
        normalized_root = self.normalize(root)
        return (
            normalized_path == normalized_root
            or normalized_path.startswith(normalized_root + os.sep)
        )
