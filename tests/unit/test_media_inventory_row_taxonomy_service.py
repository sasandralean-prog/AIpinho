from __future__ import annotations

from aipinho.services.artifacts.media_inventory_row_taxonomy_service import MediaInventoryRowTaxonomyService


def _attribute(value: object) -> dict:
    return {"value": value, "status": "observed", "evidence_ref": "file:test"}


def _entity(entity_id: str, *, name: str, extension: str, root: str, relative_path: str) -> dict:
    return {
        "entity_id": entity_id,
        "entity_kind": "file",
        "source_root": root,
        "source_root_role": "library_root",
        "relative_path": relative_path,
        "observed_attributes": {
            "name": _attribute(name),
            "extension": _attribute(extension),
            "relative_path": _attribute(relative_path),
            "source_root": _attribute(root),
            "source_root_role": _attribute("library_root"),
        },
        "evidence_refs": [f"file:{root}/{relative_path}"],
    }


def test_row_taxonomy_separates_primary_sidecar_artwork_and_candidates(tmp_path) -> None:
    audio_path = tmp_path / "A Day To Remember - All I Want.m4a"
    audio_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    duplicate_path = tmp_path / "505 - 2.m4a"
    duplicate_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    lyrics_path = tmp_path / "A Day To Remember - All I Want.lrc"
    lyrics_path.write_text("[00:01.00]sample", encoding="utf-8")
    art_path = tmp_path / "cover.jpg"
    art_path.write_bytes(bytes.fromhex("ffd8ff") + b"jpg")

    entities = [
        _entity("audio_1", name=audio_path.name, extension="m4a", root=str(tmp_path), relative_path=audio_path.name),
        _entity("audio_2", name=duplicate_path.name, extension="m4a", root=str(tmp_path), relative_path=duplicate_path.name),
        _entity("lrc_1", name=lyrics_path.name, extension="lrc", root=str(tmp_path), relative_path=lyrics_path.name),
        _entity("art_1", name=art_path.name, extension="jpg", root=str(tmp_path), relative_path=art_path.name),
    ]
    bindings = {
        "audio_1": {
            "track_title": [{"value": "All I Want", "evidence_refs": ["evidence:title"]}],
            "artist": [{"value": "A Day To Remember", "evidence_refs": ["evidence:artist"]}],
        }
    }
    perception_payload = {
        "attribute_observations": [
            {
                "entity_id": "audio_2",
                "capability_id": "media_metadata_reader",
                "observation_state": "observed",
                "canonical_key": "duration",
                "observed_value": 1000,
                "provenance": {"backend_id": "mutagen"},
            }
        ]
    }

    result = MediaInventoryRowTaxonomyService().classify(
        selected_entities=entities,
        claim_evidence_bindings=bindings,
        perception_payload=perception_payload,
    )

    rows = result["rows_by_entity"]
    assert rows["audio_1"]["row_class"] == "primary_media_with_governed_identity"
    assert rows["audio_2"]["row_class"] == "primary_media_without_identity_tags"
    assert rows["audio_2"]["candidate_truth_status"] == "candidate_only_not_truth"
    assert "duplicate_suffix_candidate" in rows["audio_2"]["candidate_risk_flags"]
    assert rows["lrc_1"]["row_class"] == "lyrics_sidecar_candidate"
    assert rows["lrc_1"]["relationship_candidate_refs"] == "candidate_audio:audio_1"
    assert rows["art_1"]["row_class"] == "artwork_candidate"
    assert result["summary"]["primary_media_row_count"] == 2
    assert result["summary"]["primary_media_with_governed_identity_count"] == 1
    assert result["summary"]["lyrics_sidecar_row_count"] == 1
    assert result["summary"]["artwork_row_count"] == 1
    assert result["summary"]["candidate_identity_not_truth_count"] == result["summary"]["candidate_identity_available_count"]


def test_file_anatomy_detects_declared_m4a_with_ebml_content_as_routing_hint(tmp_path) -> None:
    mismatch = tmp_path / "declared_audio.m4a"
    mismatch.write_bytes(bytes.fromhex("1a45dfa3") + b"webm-ish")
    entity = _entity("entity_1", name=mismatch.name, extension="m4a", root=str(tmp_path), relative_path=mismatch.name)

    result = MediaInventoryRowTaxonomyService().classify(
        selected_entities=[entity],
        claim_evidence_bindings={},
        perception_payload={"attribute_observations": []},
    )

    row = result["rows_by_entity"]["entity_1"]
    assert row["row_class"] == "primary_media_backend_no_valid_evidence"
    assert row["observed_signature_family"] == "ebml_candidate"
    assert row["observed_container"] == "matroska_or_webm_candidate"
    assert row["extension_container_mismatch"] is True
    assert row["semantic_truth_claim"] is False
    assert row["routing_hint_only"] is True
    assert result["summary"]["file_anatomy_extension_container_mismatch_count"] == 1
