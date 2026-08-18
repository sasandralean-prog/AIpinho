from __future__ import annotations


class ArtifactWriteTraceService:
    def merge(self, *chunks: list[str]) -> list[str]:
        merged: list[str] = []
        for chunk in chunks:
            merged.extend(str(item) for item in chunk)
        return list(dict.fromkeys(merged))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_write_trace"}
