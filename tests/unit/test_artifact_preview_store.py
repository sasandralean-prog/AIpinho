from artifact_fixtures import artifact_service, artifact_workspace, preview_request


def test_artifact_preview_store_save_get_list_trace_and_sanitize(tmp_path):
    workspace = artifact_workspace(tmp_path)
    service = artifact_service(tmp_path)
    preview = service.create_preview(preview_request(workspace, content="api_key=abc123"))
    fetched = service.get_preview(preview.preview_id)
    assert fetched is not None
    assert "api_key=abc123" not in fetched.content_preview
    assert service.get_trace(preview.preview_id)
    assert service.list_previews(limit=10)
