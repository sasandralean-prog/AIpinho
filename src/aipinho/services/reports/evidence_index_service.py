from __future__ import annotations

import fnmatch
from collections import defaultdict

from aipinho.schemas.reports.evidence_citation import EvidenceCitation


def matches_path(path: str, pattern: str) -> bool:
    normalized_path = path.replace(chr(92), "/")
    normalized_pattern = pattern.replace(chr(92), "/")
    variants = {normalized_pattern}
    if "**/" in normalized_pattern:
        variants.add(normalized_pattern.replace("**/", ""))
    if "/**/" in normalized_pattern:
        variants.add(normalized_pattern.replace("/**/", "/"))
    if normalized_pattern.endswith("/**"):
        variants.add(normalized_pattern[:-3])
    if normalized_pattern.endswith("/**/"):
        variants.add(normalized_pattern[:-4])
    for variant in variants:
        if fnmatch.fnmatch(normalized_path, variant):
            return True
        if variant.endswith("/**") and normalized_path.startswith(variant[:-3].rstrip("/") + "/"):
            return True
        if "/__pycache__/**" in variant and "/__pycache__" in normalized_path:
            return True
    return False


class EvidenceIndexService:
    def __init__(self, evidence: list[EvidenceCitation] | None = None) -> None:
        self.evidence = evidence or []
        self.by_path: dict[str, list[EvidenceCitation]] = defaultdict(list)
        self.by_source_type: dict[str, list[EvidenceCitation]] = defaultdict(list)
        self.build_index(self.evidence)

    def build_index(self, evidence_list: list[EvidenceCitation]) -> "EvidenceIndexService":
        self.evidence = list(evidence_list)
        self.by_path = defaultdict(list)
        self.by_source_type = defaultdict(list)
        for item in self.evidence:
            if item.path:
                self.by_path[item.path].append(item)
            self.by_source_type[item.source_type].append(item)
        return self

    def find_by_path(self, path: str) -> list[EvidenceCitation]:
        return list(self.by_path.get(path.replace(chr(92), "/"), []))

    def find_by_pattern(self, pattern: str) -> list[EvidenceCitation]:
        return [item for item in self.evidence if item.path and matches_path(item.path, pattern)]

    def find_by_source_type(self, source_type: str) -> list[EvidenceCitation]:
        return list(self.by_source_type.get(source_type, []))

    def paths(self) -> list[str]:
        return sorted(self.by_path.keys())

    def summarize(self) -> dict[str, object]:
        return {
            "evidence_count": len(self.evidence),
            "path_count": len(self.by_path),
            "source_types": {key: len(value) for key, value in sorted(self.by_source_type.items())},
            "vectorstore_enabled": False,
            "embedding_enabled": False,
            "memory_persisted": False,
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "evidence_index", **self.summarize()}
