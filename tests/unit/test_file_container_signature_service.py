from __future__ import annotations

from aipinho.services.artifacts.file_container_signature_service import FileContainerSignatureService


def _attribute(value: object) -> dict:
    return {"value": value, "status": "observed", "evidence_ref": "file:test"}


def _entity(entity_id: str, *, name: str, extension: str, root: str, relative_path: str) -> dict:
    return {
        "entity_id": entity_id,
        "entity_kind": "file",
        "source_root": root,
        "relative_path": relative_path,
        "observed_attributes": {
            "name": _attribute(name),
            "extension": _attribute(extension),
            "relative_path": _attribute(relative_path),
            "source_root": _attribute(root),
        },
    }


def test_declared_m4a_with_ftyp_signature_matches_container(tmp_path) -> None:
    path = tmp_path / "matched.m4a"
    path.write_bytes(b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 16)

    result = FileContainerSignatureService().observe_entity(
        _entity("audio_1", name=path.name, extension="m4a", root=str(tmp_path), relative_path=path.name)
    )

    assert result["observed_signature_family"] == "iso_bmff"
    assert result["observed_container_candidate"] == "mp4_or_m4a_candidate"
    assert result["extension_container_match"] is True
    assert result["file_anatomy_reason_code"] == "FILE_CONTAINER_EXTENSION_MATCHED"
    assert result["routing_hint_only"] is True
    assert result["semantic_truth_claim"] is False


def test_declared_m4a_with_ebml_signature_is_mismatch_not_identity(tmp_path) -> None:
    path = tmp_path / "declared_audio.m4a"
    path.write_bytes(bytes.fromhex("1a45dfa3") + b"webm-ish")

    result = FileContainerSignatureService().observe_entity(
        _entity("audio_1", name=path.name, extension="m4a", root=str(tmp_path), relative_path=path.name)
    )

    assert result["observed_signature_family"] == "ebml_candidate"
    assert result["observed_container_candidate"] == "matroska_or_webm_candidate"
    assert result["extension_container_mismatch"] is True
    assert result["mismatch_reason_code"] == "FILE_CONTAINER_EXTENSION_MISMATCH"
    assert "container_aware_backend_required" in result["backend_routing_implications"]
    assert result["capability_authority_bypassed"] is False
    assert result["semantic_truth_claim"] is False


def test_unknown_signature_remains_unknown_not_false_unsupported(tmp_path) -> None:
    path = tmp_path / "opaque.bin"
    path.write_bytes(b"\x01\x02opaque")

    result = FileContainerSignatureService().observe_entity(
        _entity("file_1", name=path.name, extension="bin", root=str(tmp_path), relative_path=path.name)
    )

    assert result["observed_signature_family"] == "unknown"
    assert result["file_anatomy_reason_code"] == "FILE_CONTAINER_SIGNATURE_UNKNOWN"
    assert result["extension_container_mismatch"] is False
    assert result["routing_hint_only"] is True
    assert result["semantic_truth_claim"] is False
