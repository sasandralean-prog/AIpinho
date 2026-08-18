from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def image_payload(name: str = "api_screen.png") -> dict:
    return {
        "source_ref": {
            "source_type": "test_fixture",
            "path": f"tests/fixtures/{name}",
            "file_name": name,
            "mime_type": "image/png",
            "content_hash": "c" * 64,
        },
        "file_name": name,
        "mime_type": "image/png",
        "file_size_bytes": 128,
        "metadata": {},
    }


def test_vision_ocr_and_vision_rag_status_endpoints():
    vision = client.get("/api/v1/vision/status")
    ocr = client.get("/api/v1/ocr/status")
    vision_rag = client.get("/api/v1/vision-rag/status")

    assert vision.status_code == 200
    assert vision.json()["raw_image_memory_enabled"] is False
    assert ocr.status_code == 200
    assert ocr.json()["confidence_required"] is True
    assert vision_rag.status_code == 200
    assert vision_rag.json()["vision_rag"]["vision_rag_enabled"] is True


def test_vision_analyze_endpoint_returns_citation_evidence_and_trace():
    response = client.post("/api/v1/vision/analyze", json={"image": image_payload(), "prompt": "describe"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "degraded"}
    assert body["result"]["citations"]
    assert body["result"]["evidence"]
    assert body["result"]["trace_id"]


def test_ocr_extract_endpoint_returns_cited_text_block():
    response = client.post("/api/v1/ocr/extract", json={"image": image_payload("api_ocr.png"), "metadata": {"mock_text": "Visible OCR", "confidence": 0.9}})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"]["text_blocks"][0]["citation"]
    assert body["result"]["text_blocks"][0]["confidence"] == 0.9


def test_vision_rag_preview_endpoint_never_writes_index():
    vision = client.post("/api/v1/vision/analyze", json={"image": image_payload("api_rag.png"), "prompt": "describe"}).json()["result"]
    preview = client.post("/api/v1/vision-rag/ingest-preview", json={"result": vision, "target_namespace": "vision_rag"})

    assert preview.status_code == 200
    body = preview.json()
    assert body["status"] == "ready"
    assert body["would_write_index"] is False
    assert body["approval_required"] is True
