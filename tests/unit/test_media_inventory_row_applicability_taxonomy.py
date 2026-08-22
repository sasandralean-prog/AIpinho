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


def test_sidecar_and_artwork_rows_do_not_expand_primary_media_denominator(tmp_path) -> None:
    audio_path = tmp_path / "Song.m4a"
    audio_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    lyrics_path = tmp_path / "Song.lrc"
    lyrics_path.write_text("[00:01.00]sample", encoding="utf-8")
    art_path = tmp_path / "cover.jpg"
    art_path.write_bytes(bytes.fromhex("ffd8ff") + b"jpg")
    entities = [
        _entity("audio", name=audio_path.name, extension="m4a", root=str(tmp_path), relative_path=audio_path.name),
        _entity("lyrics", name=lyrics_path.name, extension="lrc", root=str(tmp_path), relative_path=lyrics_path.name),
        _entity("art", name=art_path.name, extension="jpg", root=str(tmp_path), relative_path=art_path.name),
    ]
    bindings = {"audio": {"track_title": [{"value": "Song", "evidence_refs": ["evidence:title"]}]}}

    result = MediaInventoryRowTaxonomyService().classify(
        selected_entities=entities,
        claim_evidence_bindings=bindings,
        perception_payload={"attribute_observations": []},
    )

    assert result["summary"]["all_rows_count"] == 3
    assert result["summary"]["primary_media_row_count"] == 1
    assert result["summary"]["lyrics_sidecar_row_count"] == 1
    assert result["summary"]["artwork_row_count"] == 1
    assert result["rows_by_entity"]["lyrics"]["row_class"] == "lyrics_sidecar_candidate"
    assert result["rows_by_entity"]["art"]["row_class"] == "artwork_candidate"


def test_suspicious_lrc_collision_remains_relationship_candidate_not_truth(tmp_path) -> None:
    audio_path = tmp_path / "K.m4a"
    audio_path.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    first = tmp_path / "lyrics_a" / "K.lrc"
    second = tmp_path / "lyrics_b" / "K.lrc"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("[00:01.00]sample", encoding="utf-8")
    second.write_text("[00:02.00]sample", encoding="utf-8")
    entities = [
        _entity("audio", name=audio_path.name, extension="m4a", root=str(tmp_path), relative_path=audio_path.name),
        _entity("lrc_1", name=first.name, extension="lrc", root=str(tmp_path), relative_path="lyrics_a/K.lrc"),
        _entity("lrc_2", name=second.name, extension="lrc", root=str(tmp_path), relative_path="lyrics_b/K.lrc"),
    ]

    result = MediaInventoryRowTaxonomyService().classify(
        selected_entities=entities,
        claim_evidence_bindings={},
        perception_payload={"attribute_observations": []},
    )

    for entity_id in ("lrc_1", "lrc_2"):
        row = result["rows_by_entity"][entity_id]
        assert row["relationship_candidate_refs"] == "candidate_audio:audio"
        assert row["sidecar_relationship_truth_status"] == "candidate_only_not_truth"
        assert "LYRICS_SIDECAR_SUSPICIOUS_COLLISION" in row["sidecar_relationship_risk_flags"]
