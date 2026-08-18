from __future__ import annotations

from aipinho.schemas.patching.patch_evidence import PatchEvidence


class AffectedFileResolver:
    def resolve(self, explicit_paths: list[str], evidence: list[PatchEvidence]) -> list[str]:
        paths = list(explicit_paths)
        for item in evidence:
            if item.source_path:
                paths.append(item.source_path)
        return list(dict.fromkeys(paths))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "affected_file_resolver"}
