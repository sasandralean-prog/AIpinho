from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from pathlib import Path
from apps.launcher.ui.api.artifact_client import ArtifactClient
from apps.launcher.ui.api.base_client import ApiResult


def test_artifact_client_upload_download_zip(tmp_path: Path) -> None:
    client = ArtifactClient("http://127.0.0.1:9098", token="tok", transport=transport(data={"status": "ok"}))
    assert client.upload_text("a.txt", "conteudo").ok
    assert client.metadata("artifact_1").ok
    assert client.create_zip(["artifact_1"]).ok
    assert client.save_download(ApiResult(True, 200, b"abc"), tmp_path / "a.txt") is True
