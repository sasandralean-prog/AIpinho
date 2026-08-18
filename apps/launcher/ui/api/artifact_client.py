from __future__ import annotations

from pathlib import Path

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class ArtifactClient(BaseClient):
    def upload_text(self, filename: str, content: str, message_id: str | None = None) -> ApiResult:
        return self.post("/api/v1/artifacts/upload", {"filename": filename, "content": content, "content_type": "text/plain", "message_id": message_id})
    def metadata(self, artifact_id: str) -> ApiResult: return self.get(f"/api/v1/artifacts/{artifact_id}/metadata")
    def download(self, artifact_id: str) -> ApiResult: return self.get(f"/api/v1/artifacts/{artifact_id}/download")
    def download_endpoint(self, endpoint: str) -> ApiResult:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return self.get(path)
    def create_zip(self, artifact_ids: list[str], filename: str = "artifacts.zip") -> ApiResult: return self.post("/api/v1/artifacts/zip", {"artifact_ids": artifact_ids, "filename": filename})
    def save_download(self, result: ApiResult, target: Path) -> bool:
        if not result.ok:
            return False
        data = result.data if isinstance(result.data, (bytes, bytearray)) else str(result.data).encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(data))
        return True
