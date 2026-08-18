from __future__ import annotations

from pathlib import Path

from apps.launcher.ui.api.artifact_client import ArtifactClient
from apps.launcher.ui.api.base_client import ApiResult
from apps.launcher.ui.presentation.chat_presentation_mapper import ChatPresentationMapper


def test_chat_normal_text_hides_raw_technical_keys_and_token() -> None:
    mapper = ChatPresentationMapper()
    payload = {
        "timeline": {
            "session_id": "chat_1",
            "messages": [
                {"role": "user", "message_id": "msg_user", "content": "Quanto e 2+2?", "raw_available": False},
                {
                    "role": "assistant",
                    "message_id": "msg_assistant",
                    "content": "4",
                    "metadata": {"raw_default_visible": False, "endpoint_ref": "/api/v1/chat", "token": "secret-token"},
                },
            ],
        }
    }

    text = mapper.normal_text(payload)

    assert "Voce:" in text
    assert "AIpinho:" in text
    assert "4" in text
    assert "raw_default_visible" not in text
    assert "endpoint_ref" not in text
    assert "secret-token" not in text


def test_artifact_button_requires_artifact_id() -> None:
    mapper = ChatPresentationMapper()
    payload = {
        "presentation": {
            "messages": [
                {
                    "role": "assistant",
                    "label": "AIpinho",
                    "text": "Arquivo pronto.",
                    "artifacts": [
                        {"filename": "resposta.txt", "label": "Baixar resposta.txt"},
                        {"artifact_id": "artifact_1", "filename": "artifacts.zip", "label": "Baixar artifacts.zip"},
                    ],
                }
            ]
        }
    }

    presentation = mapper.map(payload)
    artifacts = presentation.messages[0].artifacts

    assert artifacts[0].actionable is False
    assert "sem id acionavel" in (artifacts[0].detail or "")
    assert artifacts[1].actionable is True
    assert artifacts[1].artifact_id == "artifact_1"


def test_json_like_message_uses_human_field_in_normal_mode() -> None:
    mapper = ChatPresentationMapper()
    payload = {
        "timeline": {
            "messages": [
                {
                    "role": "assistant",
                    "content": '{"metadata": {"raw_default_visible": false}, "summary": "Resposta humana limpa."}',
                }
            ]
        }
    }

    text = mapper.normal_text(payload)

    assert "Resposta humana limpa." in text
    assert "raw_default_visible" not in text


def test_artifact_download_uses_authorization_header_and_saves_file(tmp_path: Path) -> None:
    calls = []

    def transport(method, url, headers, body, timeout):
        calls.append({"method": method, "url": url, "headers": headers})
        return 200, b"abc"

    client = ArtifactClient("http://127.0.0.1:9098", token="local-token", transport=transport)
    result = client.download("artifact_1")

    assert result.ok is True
    assert calls[0]["headers"]["Authorization"] == "Bearer local-token"
    assert client.save_download(ApiResult(True, 200, result.data), tmp_path / "artifact.bin") is True
    assert (tmp_path / "artifact.bin").read_bytes() == b"abc"
