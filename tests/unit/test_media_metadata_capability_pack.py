from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from aipinho.capabilities.media_metadata.adapter import MediaMetadataObserverAdapter
from aipinho.capabilities.media_metadata.backends import (
    FFprobeMediaMetadataBackend,
    MutagenMediaMetadataBackend,
    NativeMinimalMediaProbeBackend,
)
from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_IDENTITY_CANONICAL_KEYS,
    MEDIA_METADATA_CANONICAL_KEYS,
    MEDIA_METADATA_EVIDENCE_KEYS,
    MediaMetadataBackendError,
    MediaMetadataBackendDescriptor,
    MediaMetadataBackendPolicy,
    RawMediaMetadataField,
    RawMediaMetadataResult,
    media_metadata_capability_descriptor,
)
from aipinho.capabilities.media_metadata.environment import (
    MEDIA_TOOL_STATUS_AVAILABLE,
    MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
    MEDIA_TOOL_STATUS_UNAVAILABLE,
    MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR,
    MediaToolDiscoveryResult,
    discover_media_tool,
    media_environment_snapshot,
)
from aipinho.capabilities.media_metadata.normalizer import MediaMetadataNormalizer
from aipinho.capabilities.media_metadata.policy import MediaMetadataCapability
from aipinho.schemas.artifacts.contract_perception import ObservationExecutionPolicy, ObservationGoal, ObservationStrategy, ObservationTask
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _task(file_path: Path, **updates) -> ObservationTask:
    data = {
        "goal_id": "goal_media_metadata",
        "strategy_id": "strategy_execute_observer",
        "capability_id": "media_metadata_reader",
        "entity_ref": {
            "entity_id": "entity_audio_1",
            "entity_role": "media_asset_candidate",
            "source_root_role": "library_root",
            "path": str(file_path),
        },
        "attribute_name": "codec",
        "canonical_key": "codec",
        "inputs": {
            "file_path": str(file_path),
            "entity_role": "media_asset_candidate",
            "source_root_role": "library_root",
            "required_confidence": 0.0,
        },
        "expected_outputs": ["codec", "container", "duration"],
        "expected_evidence": ["media_metadata_evidence"],
        "status": "READY_FOR_OBSERVER",
    }
    data.update(updates)
    return ObservationTask(**data)


def _minimal_mp4_bytes(*, brand: bytes = b"M4A ", duration_seconds: int | None = None, codec: bytes | None = None) -> bytes:
    ftyp = (24).to_bytes(4, "big") + b"ftyp" + brand + b"\x00\x00\x00\x00" + brand + b"isom"
    chunks = [ftyp]
    if duration_seconds is not None:
        mvhd_payload = b"\x00\x00\x00\x00" + b"\x00" * 8 + (1000).to_bytes(4, "big") + (duration_seconds * 1000).to_bytes(4, "big")
        chunks.append((len(mvhd_payload) + 8).to_bytes(4, "big") + b"mvhd" + mvhd_payload)
    if codec is not None:
        stsd_payload = b"\x00" * 12 + codec + b"\x00" * 16
        chunks.append((len(stsd_payload) + 8).to_bytes(4, "big") + b"stsd" + stsd_payload)
    return b"".join(chunks)


def _minimal_mp3_bytes() -> bytes:
    return bytes([0xFF, 0xFB, 0x90, 0x64]) + b"\x00" * 64


class _FakeMediaBackend:
    def __init__(
        self,
        backend_id: str,
        fields: list[RawMediaMetadataField] | None = None,
        error_code: str | None = None,
        *,
        supported_attributes: list[str] | None = None,
        status: str = "available",
    ) -> None:
        self.backend_id = backend_id
        self.fields = fields or []
        self.error_code = error_code
        self.supported_attributes = supported_attributes or list(MEDIA_METADATA_EVIDENCE_KEYS)
        self.status = status
        self.calls: list[str] = []
        self.descriptor_calls = 0

    def descriptor(self) -> MediaMetadataBackendDescriptor:
        self.descriptor_calls += 1
        return MediaMetadataBackendDescriptor(
            backend_id=self.backend_id,
            backend_type="fake",
            supported_attributes=self.supported_attributes,
            status=self.status,
            dependency_name=self.backend_id,
        )

    def probe(self, *, file_path: str, entity_ref: dict | None = None) -> RawMediaMetadataResult:
        self.calls.append(file_path)
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version="test",
            file_ref=file_path,
            entity_ref=entity_ref or {},
            raw_fields=self.fields,
            errors=[
                MediaMetadataBackendError(
                    code=self.error_code,
                    message=f"{self.backend_id} unavailable for test",
                    backend_id=self.backend_id,
                )
            ] if self.error_code else [],
            confidence_by_field={item.canonical_key: item.confidence for item in self.fields},
            raw_ref=file_path,
        )


class _FakeMutagenTextFrame:
    def __init__(self, text: object) -> None:
        self.text = text


def test_media_metadata_descriptor_declares_canonical_contract() -> None:
    capability = media_metadata_capability_descriptor()

    assert capability.capability_id == "media_metadata_reader"
    assert "media_asset_candidate" in capability.consumes
    assert "file_path" in capability.consumes
    assert {"codec", "container", "duration", "metadata"}.issubset(set(capability.produces))
    assert "observations" not in capability.produces
    assert capability.evidence_types == ["media_metadata_evidence"]
    assert "media_asset_candidate_hypothesis" in capability.preconditions
    assert capability.observer_binding["adapter_id"] == "media_metadata_reader"


def test_media_metadata_key_domains_separate_technical_metadata_from_identity() -> None:
    assert {"codec", "container", "duration", "metadata"}.issubset(set(MEDIA_METADATA_CANONICAL_KEYS))
    assert set(MEDIA_IDENTITY_CANONICAL_KEYS) == {"track_title", "artist", "album", "album_artist"}
    assert set(MEDIA_IDENTITY_CANONICAL_KEYS).isdisjoint(set(MEDIA_METADATA_CANONICAL_KEYS))
    assert set(MEDIA_IDENTITY_CANONICAL_KEYS).issubset(set(MEDIA_METADATA_EVIDENCE_KEYS))
    assert set(MEDIA_METADATA_CANONICAL_KEYS).issubset(set(MEDIA_METADATA_EVIDENCE_KEYS))


def test_media_metadata_reader_observes_identity_keys_but_native_minimal_does_not_claim_them() -> None:
    capability = media_metadata_capability_descriptor()
    native_descriptor = NativeMinimalMediaProbeBackend().descriptor()

    assert set(MEDIA_IDENTITY_CANONICAL_KEYS).issubset(set(capability.observable_attributes))
    assert set(MEDIA_IDENTITY_CANONICAL_KEYS).isdisjoint(set(native_descriptor.supported_attributes))


def test_media_inventory_contract_marks_identity_fields_semantically() -> None:
    payload = yaml.safe_load(Path("config/artifacts/artifact_semantic_contract_policy.yaml").read_text(encoding="utf-8"))
    contract = next(item for item in payload["contracts"] if item["contract_id"] == "media_corpus_inventory_artifact")
    attributes = {
        item["canonical_key"]: item
        for item in contract["attribute_contracts"]
        if item.get("canonical_key") in MEDIA_IDENTITY_CANONICAL_KEYS
    }

    assert set(attributes) == set(MEDIA_IDENTITY_CANONICAL_KEYS)
    assert all(item.get("semantic_type") == "media_identity" for item in attributes.values())


def test_media_metadata_reader_is_known_by_default_capability_registry() -> None:
    registry = CapabilityRegistry(fallback_attributes=["name", "codec"])

    capability = registry.get("media_metadata_reader")

    assert capability is not None
    assert capability.domain == "media_metadata"
    assert "codec" in capability.observable_attributes
    assert capability.observer_binding["adapter_id"] == "media_metadata_reader"


def _media_match_for(attribute: str):
    service = ContractDrivenPerceptionService()
    capability = media_metadata_capability_descriptor()
    goal = ObservationGoal(
        attribute_name=attribute,
        canonical_key=attribute,
        expected_semantic_type="media_identity" if attribute in MEDIA_IDENTITY_CANONICAL_KEYS else "technical_metadata",
        entity_ref={"source_root_roles": ["library_root"], "file_path_available": True},
        target_entity_kinds=["file"],
    )
    strategy = ObservationStrategy(
        goal_id=goal.goal_id,
        strategy_kind="execute_observer",
        attribute_name=attribute,
        canonical_key=attribute,
        required_capability_kind="media_metadata",
        rationale="unit test",
    )
    return service._score_capability_match(goal=goal, strategy=strategy, capability=capability)


def test_identity_goal_eligibility_selects_media_metadata_reader() -> None:
    for key in MEDIA_IDENTITY_CANONICAL_KEYS:
        match = _media_match_for(key)

        assert match.match_status == "MATCHED"
        assert match.capability_id == "media_metadata_reader"
        assert match.attributes_covered == [key]
        assert "media_asset_candidate_hypothesis" in match.satisfied_preconditions
        assert "precondition_missing" not in match.conflicts


def test_computed_metadata_status_fields_do_not_become_physical_media_claims() -> None:
    for key in ["metadata_status", "metadata_source", "probe_status"]:
        match = _media_match_for(key)

        assert match.match_status == "PRECONDITION_FAILED"
        assert match.capability_id == "media_metadata_reader"
        assert key in match.attributes_covered
        assert "media_asset_candidate_hypothesis" not in match.satisfied_preconditions


def test_backend_descriptors_are_declarative_and_do_not_select_entities() -> None:
    native_descriptor = NativeMinimalMediaProbeBackend().descriptor()
    ffprobe_descriptor = FFprobeMediaMetadataBackend(executable="definitely_missing_ffprobe_binary").descriptor()

    assert native_descriptor.backend_type == "native_minimal"
    assert native_descriptor.supported_extensions
    assert native_descriptor.status == "available"
    assert ffprobe_descriptor.backend_type == "external_cli"
    assert ffprobe_descriptor.status == "unavailable"
    assert ffprobe_descriptor.requires_external_binary is True


def test_mutagen_backend_reports_typed_error_when_dependency_is_absent(tmp_path: Path) -> None:
    backend = MutagenMediaMetadataBackend()
    if backend.descriptor().status != "unavailable":
        pytest.skip("mutagen is installed in this environment; absence path is not active")
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"not media")

    result = backend.probe(file_path=str(sample), entity_ref={"entity_id": "entity_1"})

    assert result.errors
    assert result.errors[0].code == "MUTAGEN_NOT_IMPORTABLE"
    assert result.raw_fields == []


def test_ffprobe_backend_reports_typed_error_when_cli_is_absent(tmp_path: Path) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"not media")

    result = FFprobeMediaMetadataBackend(executable="definitely_missing_ffprobe_binary").probe(file_path=str(sample))

    assert result.errors
    assert result.errors[0].code == "FFPROBE_NOT_AVAILABLE"
    assert result.raw_fields == []


def test_media_tool_discovery_reports_available_executable(tmp_path: Path) -> None:
    executable = tmp_path / "ffprobe.exe"
    executable.write_text("fake", encoding="utf-8")

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="ffprobe version 9.0-full_build\n", stderr="")

    result = discover_media_tool(
        "ffprobe",
        tool_id="ffprobe",
        runner=fake_runner,
        which=lambda _command: str(executable),
    )

    assert result.status == MEDIA_TOOL_STATUS_AVAILABLE
    assert result.available is True
    assert result.version == "9.0-full_build"
    assert result.resolved_executable_path == str(executable)


def test_media_tool_discovery_reports_absent_executable() -> None:
    result = discover_media_tool("ffprobe", tool_id="ffprobe", which=lambda _command: None)

    assert result.status == MEDIA_TOOL_STATUS_UNAVAILABLE
    assert result.reason_code == "FFPROBE_NOT_AVAILABLE"
    assert result.available is False


def test_media_tool_discovery_reports_invalid_resolved_executable(tmp_path: Path) -> None:
    directory = tmp_path / "ffprobe"
    directory.mkdir()

    result = discover_media_tool("ffprobe", tool_id="ffprobe", which=lambda _command: str(directory))

    assert result.status == MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE
    assert result.reason_code == "FFPROBE_EXECUTABLE_INVALID"
    assert result.available is False


def test_media_tool_discovery_reports_nonzero_version_probe(tmp_path: Path) -> None:
    executable = tmp_path / "ffprobe.exe"
    executable.write_text("fake", encoding="utf-8")

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="boom")

    result = discover_media_tool(
        "ffprobe",
        tool_id="ffprobe",
        runner=fake_runner,
        which=lambda _command: str(executable),
    )

    assert result.status == MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR
    assert result.reason_code == "FFPROBE_VERSION_OR_PROBE_ERROR"
    assert result.available is False


def test_media_tool_discovery_reports_malformed_version_probe(tmp_path: Path) -> None:
    executable = tmp_path / "ffprobe.exe"
    executable.write_text("fake", encoding="utf-8")

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="not a version banner\n", stderr="")

    result = discover_media_tool(
        "ffprobe",
        tool_id="ffprobe",
        runner=fake_runner,
        which=lambda _command: str(executable),
    )

    assert result.status == MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR
    assert result.reason_code == "FFPROBE_VERSION_OR_PROBE_ERROR"
    assert result.available is False


def test_ffprobe_descriptor_distinguishes_unusable_executable(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / "ffprobe.exe"
    executable.write_text("fake", encoding="utf-8")

    def fake_discover(*args, **kwargs):
        return MediaToolDiscoveryResult(
            tool_id="ffprobe",
            command="ffprobe",
            status=MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
            resolved_executable_path=str(executable),
            reason_code="FFPROBE_VERSION_TIMEOUT",
            message="timeout",
        )

    monkeypatch.setattr("aipinho.capabilities.media_metadata.backends.ffprobe_backend.discover_media_tool", fake_discover)

    descriptor = FFprobeMediaMetadataBackend().descriptor()

    assert descriptor.status == "executable_but_unusable"
    assert descriptor.environment_reason_code == "FFPROBE_VERSION_TIMEOUT"
    assert descriptor.resolved_executable_path == str(executable)


def test_ffprobe_backend_uses_discovered_executable(monkeypatch, tmp_path: Path) -> None:
    sample = tmp_path / "sample.m4a"
    sample.write_bytes(b"fake media")
    executable = tmp_path / "bin" / "ffprobe.exe"
    executable.parent.mkdir()
    executable.write_text("fake", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_discover(*args, **kwargs):
        return MediaToolDiscoveryResult(
            tool_id="ffprobe",
            command="ffprobe",
            status=MEDIA_TOOL_STATUS_AVAILABLE,
            resolved_executable_path=str(executable),
            version="9.0",
            version_first_line="ffprobe version 9.0",
        )

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"format":{"format_name":"mov,mp4,m4a","duration":"2.5"},"streams":[{"codec_type":"audio","codec_name":"aac","channels":2}]}',
            stderr="",
        )

    monkeypatch.setattr("aipinho.capabilities.media_metadata.backends.ffprobe_backend.discover_media_tool", fake_discover)
    monkeypatch.setattr("aipinho.capabilities.media_metadata.backends.ffprobe_backend.subprocess.run", fake_run)

    result = FFprobeMediaMetadataBackend().probe(file_path=str(sample), entity_ref={"entity_id": "entity_1"})

    assert not result.errors
    assert commands[0][0] == str(executable)
    assert result.provenance["shell"] is False
    fields = {field.canonical_key: field.normalized_value for field in result.raw_fields}
    assert fields["container"] == "mov"
    assert fields["codec"] == "aac"
    assert fields["duration"] == "2.5"


def test_media_environment_snapshot_reports_ffmpeg_and_ffprobe() -> None:
    snapshot = media_environment_snapshot()

    assert set(snapshot) == {"ffmpeg", "ffprobe"}
    assert snapshot["ffmpeg"]["status"] in {
        MEDIA_TOOL_STATUS_AVAILABLE,
        MEDIA_TOOL_STATUS_UNAVAILABLE,
        MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
        MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR,
    }
    assert snapshot["ffprobe"]["status"] in {
        MEDIA_TOOL_STATUS_AVAILABLE,
        MEDIA_TOOL_STATUS_UNAVAILABLE,
        MEDIA_TOOL_STATUS_EXECUTABLE_BUT_UNUSABLE,
        MEDIA_TOOL_STATUS_VERSION_OR_PROBE_ERROR,
    }


def test_native_minimal_backend_detects_mp4_container_duration_and_codec_from_headers(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_mp4_bytes(duration_seconds=123, codec=b"mp4a"))

    result = NativeMinimalMediaProbeBackend().probe(file_path=str(sample), entity_ref={"entity_id": "entity_1"})

    fields = {item.canonical_key: item.normalized_value for item in result.raw_fields}
    assert fields["container"] == "m4a"
    assert fields["codec"] == "mp4a"
    assert fields["duration"] == 123.0


def test_native_minimal_backend_detects_mp3_basic_frame_without_tags(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_mp3_bytes())

    result = NativeMinimalMediaProbeBackend().probe(file_path=str(sample), entity_ref={"entity_id": "entity_1"})

    fields = {item.canonical_key: item.normalized_value for item in result.raw_fields}
    assert fields["container"] == "mp3"
    assert fields["codec"] == "mp3"
    assert fields["sample_rate"] == 44100
    assert fields["channels"] == 2


def test_native_minimal_backend_does_not_invent_codec_or_duration(tmp_path: Path) -> None:
    sample = tmp_path / "sample.m4a"
    sample.write_bytes(_minimal_mp4_bytes(duration_seconds=None, codec=None))

    result = NativeMinimalMediaProbeBackend().probe(file_path=str(sample), entity_ref={"entity_id": "entity_1"})

    fields = {item.canonical_key: item.normalized_value for item in result.raw_fields}
    assert fields["container"] == "m4a"
    assert "codec" not in fields
    assert "duration" not in fields


def test_native_minimal_backend_does_not_use_extension_as_metadata(tmp_path: Path) -> None:
    for filename, content in {
        "fake.m4a": b"plain text pretending to be media",
        "fake.mp3": b"plain text pretending to be media",
        "fake.lrc": b"[00:01.00] lyrics only",
        "fake.jpg": b"not a parsed media container",
    }.items():
        sample = tmp_path / filename
        sample.write_bytes(content)

        result = NativeMinimalMediaProbeBackend().probe(file_path=str(sample), entity_ref={"entity_id": filename})

        assert result.raw_fields == []
        assert result.errors
        assert result.errors[0].code in {"MEDIA_BACKEND_UNSUPPORTED_FORMAT", "MEDIA_BACKEND_NO_EVIDENCE"}


def test_normalizer_generates_evidence_only_for_supported_confident_fields() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(canonical_key="duration", normalized_value=12.5, confidence=0.9, source_backend_id="fake_backend", raw_ref="fake://media"),
            RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.2, source_backend_id="fake_backend", raw_ref="fake://media"),
            RawMediaMetadataField(canonical_key="unknown_field", normalized_value="x", confidence=1.0, source_backend_id="fake_backend", raw_ref="fake://media"),
        ],
        confidence_by_field={"duration": 0.9, "codec": 0.2, "unknown_field": 1.0},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    assert evidence.canonical_keys == ["duration"]
    record = evidence.records[0]
    assert record.source == "media_file"
    assert record.acquisition_method == "media_metadata_parse"
    assert record.backend_id == "fake_backend"
    assert record.capability_id == "media_metadata_reader"
    assert record.raw_ref == "fake://media"


def test_normalizer_expands_backend_tags_into_claim_level_identity_evidence() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="metadata",
                normalized_value={
                    "TIT2": ["Song Title"],
                    "ARTIST": "Artist Name",
                    "ALBUM": "Album Name",
                    "aART": "Album Artist",
                    "COMMENT": "not an identity claim",
                },
                confidence=0.9,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
                semantic_type="descriptive_metadata",
            )
        ],
        confidence_by_field={"metadata": 0.9},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    records = {record.canonical_key: record for record in evidence.records}
    assert records["metadata"].semantic_type == "descriptive_metadata"
    assert records["track_title"].normalized_value == "Song Title"
    assert records["track_title"].semantic_type == "media_identity"
    assert records["track_title"].provenance["raw_tag_key"] == "TIT2"
    assert records["track_title"].provenance["semantic_mapper"] == "media_metadata_identity_tag_mapper_v1"
    assert records["artist"].normalized_value == "Artist Name"
    assert records["album"].normalized_value == "Album Name"
    assert records["album_artist"].normalized_value == "Album Artist"
    assert "comment" not in {str(key).casefold() for key in records}


def test_low_confidence_metadata_does_not_get_promoted_to_identity_evidence() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="metadata",
                normalized_value={"ARTIST": "Low Confidence Artist"},
                confidence=0.2,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
                semantic_type="descriptive_metadata",
            )
        ],
        confidence_by_field={"metadata": 0.2},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    assert evidence.records == []
    assert evidence.canonical_keys == []


def test_identity_evidence_from_independent_backends_is_preserved() -> None:
    raw_results = [
        RawMediaMetadataResult(
            backend_id=backend_id,
            backend_version="1",
            file_ref="fake://media",
            entity_ref={"entity_id": "entity_1"},
            raw_fields=[
                RawMediaMetadataField(
                    canonical_key="metadata",
                    normalized_value={"ARTIST": "Corroborated Artist"},
                    confidence=0.9,
                    source_backend_id=backend_id,
                    raw_ref=f"fake://media#{backend_id}",
                    semantic_type="descriptive_metadata",
                )
            ],
            confidence_by_field={"metadata": 0.9},
            raw_ref=f"fake://media#{backend_id}",
        )
        for backend_id in ["mutagen", "ffprobe"]
    ]

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=raw_results,
        entity_ref={"entity_id": "entity_1"},
    )

    artist_records = [record for record in evidence.records if record.canonical_key == "artist"]
    assert len(artist_records) == 2
    assert {record.backend_id for record in artist_records} == {"mutagen", "ffprobe"}
    assert {record.raw_ref for record in artist_records} == {"fake://media#mutagen", "fake://media#ffprobe"}


def test_mutagen_tag_extraction_preserves_safe_text_frame_structure() -> None:
    backend = MutagenMediaMetadataBackend()
    tags = {
        "TPE1": _FakeMutagenTextFrame(["Artist One", "Artist Two"]),
        "TIT2": ["Song Title"],
        "APIC:cover": _FakeMutagenTextFrame(["binary artwork"]),
    }

    rows = backend._tags_to_dict(tags)

    assert rows["TPE1"] == ["Artist One", "Artist Two"]
    assert rows["TIT2"] == ["Song Title"]
    assert "APIC:cover" not in rows


def test_mp4_copyright_aliases_do_not_accept_plain_art_nam_alb_tags() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="metadata",
                normalized_value={
                    "\xa9ART": "Copyright Artist",
                    "ART": "Plain Art",
                    "NAM": "Plain Name",
                    "ALB": "Plain Album",
                },
                confidence=0.9,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
                semantic_type="descriptive_metadata",
            )
        ],
        confidence_by_field={"metadata": 0.9},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    identity_records = [record for record in evidence.records if record.semantic_type == "media_identity"]
    assert [(record.canonical_key, record.normalized_value) for record in identity_records] == [
        ("artist", "Copyright Artist")
    ]


def test_generic_metadata_record_does_not_become_identity_without_mapped_tag() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="metadata",
                normalized_value={"performer_name": "Artist Name"},
                confidence=0.9,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
                semantic_type="descriptive_metadata",
            )
        ],
        confidence_by_field={"metadata": 0.9},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    assert evidence.canonical_keys == ["metadata"]


def test_set_like_identity_tag_provenance_is_deterministic_and_typed() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="metadata",
                normalized_value={"ARTIST": {"Beta Artist", "Alpha Artist"}},
                confidence=0.9,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
                semantic_type="descriptive_metadata",
            )
        ],
        confidence_by_field={"metadata": 0.9},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    artist = next(record for record in evidence.records if record.canonical_key == "artist")
    assert artist.normalized_value == "Alpha Artist; Beta Artist"
    assert artist.provenance["raw_tag_value_source_type"] == "set"
    assert artist.provenance["raw_tag_value_set_like"] is True
    assert artist.provenance["raw_tag_value_repr"] == "['Alpha Artist', 'Beta Artist']"


def test_media_metadata_normalizer_does_not_produce_artifact_observations_notes() -> None:
    raw = RawMediaMetadataResult(
        backend_id="fake_backend",
        backend_version="1",
        file_ref="fake://media",
        entity_ref={"entity_id": "entity_1"},
        raw_fields=[
            RawMediaMetadataField(
                canonical_key="observations",
                normalized_value="diagnostic note",
                confidence=1.0,
                source_backend_id="fake_backend",
                raw_ref="fake://media",
            )
        ],
        confidence_by_field={"observations": 1.0},
        raw_ref="fake://media",
    )

    evidence = MediaMetadataNormalizer(policy=MediaMetadataBackendPolicy(min_confidence=0.7)).normalize(
        raw_results=[raw],
        entity_ref={"entity_id": "entity_1"},
    )

    assert evidence.records == []
    assert evidence.canonical_keys == []


def test_media_metadata_adapter_rejects_ineligible_entities_via_boundary(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_mp3_bytes())
    adapter = MediaMetadataObserverAdapter(
        capability=MediaMetadataCapability(
            backend_policy=MediaMetadataBackendPolicy(primary="native_minimal", fallbacks=[]),
            backends={"native_minimal": NativeMinimalMediaProbeBackend()},
        )
    )
    boundary = ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter})
    task = _task(sample, inputs={"file_path": str(sample), "entity_role": "source_code_file", "source_root_role": "project_root"})

    result = boundary.execute(task=task, capability=media_metadata_capability_descriptor())

    assert result.status == "BLOCKED_OBSERVER_ERROR"
    assert result.errors[0].code == "MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED"
    assert result.evidence_set.records == []


def test_observation_execution_boundary_runs_media_capability_and_returns_evidence(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(_minimal_mp3_bytes())
    adapter = MediaMetadataObserverAdapter(
        capability=MediaMetadataCapability(
            backend_policy=MediaMetadataBackendPolicy(primary="native_minimal", fallbacks=[], min_confidence=0.6),
            backends={"native_minimal": NativeMinimalMediaProbeBackend()},
        )
    )
    boundary = ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter})

    result = boundary.execute(
        task=_task(sample),
        capability=media_metadata_capability_descriptor(),
        policy=ObservationExecutionPolicy(min_confidence=0.6),
    )

    assert result.status == "EXECUTED"
    assert result.errors == []
    keys = {record.canonical_key for record in result.evidence_set.records}
    assert {"container", "codec", "sample_rate", "channels"}.issubset(keys)
    assert all(record.backend_id == "native_minimal" for record in result.evidence_set.records)
    assert all(record.capability_id == "media_metadata_reader" for record in result.evidence_set.records)
    assert result.raw_ref == str(sample)


def test_summary_media_metadata_capability_section_aggregates_lightweight_status() -> None:
    service = UniversalTaskSessionService()

    summary = service._media_metadata_capability_summary(
        [
            {
                "status": "partial",
                "capability_id": "media_metadata_reader",
                "primary_backend": "mutagen",
                "selected_backend": "native_minimal",
                "available_backends": ["native_minimal"],
                "blocked_backends": ["mutagen"],
                "globally_blocked_backends": ["mutagen"],
                "partially_blocked_backends": [],
                "missing_dependency": ["MEDIA_BACKEND_NOT_AVAILABLE"],
                "attempted_backends": ["mutagen", "native_minimal"],
                "successful_backends": ["native_minimal"],
                "fallback_backends_used": ["native_minimal"],
                "backend_error_counts": {"MEDIA_BACKEND_NOT_AVAILABLE": 1},
                "evidence_records_created": 2,
                "attributes_observed": ["container", "codec"],
                "attributes_missing": ["duration"],
                "limitations": ["minimal probe"],
            }
        ]
    )

    assert summary["status"] == "partial"
    assert summary["capability_id"] == "media_metadata_reader"
    assert summary["selected_backend"] == "native_minimal"
    assert summary["evidence_records_created"] == 2
    assert summary["attributes_observed"] == ["codec", "container"]
    assert summary["missing_dependency"] == ["MEDIA_BACKEND_NOT_AVAILABLE"]
    assert summary["primary_backend"] == "mutagen"
    assert summary["globally_blocked_backends"] == ["mutagen"]
    assert summary["partially_blocked_backends"] == []
    assert summary["attempted_backends"] == ["mutagen", "native_minimal"]
    assert summary["successful_backends"] == ["native_minimal"]
    assert summary["fallback_backends_used"] == ["native_minimal"]
    assert summary["backend_error_counts"] == {"MEDIA_BACKEND_NOT_AVAILABLE": 1}


def test_media_metadata_policy_selects_primary_and_records_fallback_semantics(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    capability = MediaMetadataCapability(
        backend_policy=MediaMetadataBackendPolicy(
            primary="mutagen",
            fallbacks=["ffprobe", "native_minimal"],
            min_confidence=0.7,
            allow_partial_evidence=True,
        ),
        backends={
            "mutagen": _FakeMediaBackend(
                "mutagen",
                [
                    RawMediaMetadataField(
                        canonical_key="codec",
                        normalized_value="aac",
                        confidence=0.95,
                        source_backend_id="mutagen",
                        raw_ref=str(sample),
                    )
                ],
            ),
            "ffprobe": _FakeMediaBackend("ffprobe", error_code="FFPROBE_NOT_AVAILABLE"),
            "native_minimal": _FakeMediaBackend(
                "native_minimal",
                [
                    RawMediaMetadataField(
                        canonical_key="container",
                        normalized_value="m4a",
                        confidence=0.8,
                        source_backend_id="native_minimal",
                        raw_ref=str(sample),
                    )
                ],
            ),
        },
    )

    payload = capability.payload_for_boundary(file_path=str(sample), entity_ref={"entity_id": "entity_1"})
    summary = payload["media_metadata_capability"]

    assert payload["media_environment"]["scope"] == "media_metadata"
    assert payload["media_environment"]["ffmpeg_required_for_media_environment"] is True
    assert payload["media_environment"]["ffprobe_required_for_metadata_backend"] is True
    assert set(payload["media_environment"]["tools"]) == {"ffmpeg", "ffprobe"}
    assert summary["primary_backend"] == "mutagen"
    assert summary["selected_backend"] == "mutagen"
    assert summary["attempted_backends"] == ["mutagen", "ffprobe", "native_minimal"]
    assert summary["successful_backends"] == ["mutagen", "native_minimal"]
    assert summary["fallback_backends_used"] == ["native_minimal"]
    assert summary["missing_dependency"] == ["ffprobe"]
    assert summary["backend_error_counts"] == {"FFPROBE_NOT_AVAILABLE": 1}
    evidence = payload["observations"]
    assert {record["backend_id"] for record in evidence} == {"mutagen", "native_minimal"}
    assert {record["canonical_key"] for record in evidence} == {"codec", "container"}


def test_demand_aware_policy_stops_after_identity_any_of_is_satisfied(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [
            RawMediaMetadataField(canonical_key="metadata", normalized_value={"TITLE": "Song", "ARTIST": "Artist"}, confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample)),
            RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample)),
        ],
    )
    ffprobe = _FakeMediaBackend("ffprobe", [RawMediaMetadataField(canonical_key="duration", normalized_value=12.0, confidence=0.9, source_backend_id="ffprobe", raw_ref=str(sample))])
    native = _FakeMediaBackend("native_minimal", [RawMediaMetadataField(canonical_key="container", normalized_value="m4a", confidence=0.8, source_backend_id="native_minimal", raw_ref=str(sample))])
    capability = MediaMetadataCapability(backends={"mutagen": mutagen, "ffprobe": ffprobe, "native_minimal": native})

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["track_title", "artist", "codec", "duration"],
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == []
    assert native.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen"]
    assert {record["canonical_key"] for record in payload["observations"]} == {"metadata", "track_title", "artist", "codec"}


def _media_demand(
    *,
    required_keys: list[str] | None = None,
    identity_keys: list[str] | None = None,
    optional_keys: list[str] | None = None,
) -> dict:
    groups = []
    if identity_keys:
        groups.append(
            {
                "semantic_type": "media_identity",
                "satisfaction": "ANY_OF",
                "candidate_keys": identity_keys,
                "minimum_evidenced_claims": 1,
            }
        )
    return {
        "blocking_required_claims": [
            {"canonical_key": key, "satisfaction": "REQUIRED", "evidence_required": True}
            for key in required_keys or []
        ],
        "semantic_requirement_groups": groups,
        "optional_enrichment_claims": optional_keys or [],
    }


def test_required_technical_claim_still_drives_fallback_after_identity_is_satisfied(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="metadata", normalized_value={"ARTIST": "Artist"}, confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
        supported_attributes=["artist", "track_title", "metadata"],
    )
    ffprobe = _FakeMediaBackend(
        "ffprobe",
        [RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="ffprobe", raw_ref=str(sample))],
        supported_attributes=["codec"],
    )
    native = _FakeMediaBackend("native_minimal", supported_attributes=["codec", "container"])
    capability = MediaMetadataCapability(
        backend_policy=MediaMetadataBackendPolicy(primary="mutagen", fallbacks=["ffprobe", "native_minimal"]),
        backends={"mutagen": mutagen, "ffprobe": ffprobe, "native_minimal": native},
    )

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["artist", "track_title", "codec"],
        media_observation_demand=_media_demand(required_keys=["codec"], identity_keys=["artist", "track_title"]),
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == [str(sample)]
    assert native.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen", "ffprobe"]
    assert {record["canonical_key"] for record in payload["observations"]} == {"metadata", "artist", "codec"}


def test_optional_technical_enrichment_does_not_force_fallback_after_identity_is_satisfied(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="metadata", normalized_value={"ARTIST": "Artist"}, confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
        supported_attributes=["artist", "track_title", "metadata"],
    )
    ffprobe = _FakeMediaBackend(
        "ffprobe",
        [RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="ffprobe", raw_ref=str(sample))],
        supported_attributes=["codec"],
    )
    capability = MediaMetadataCapability(
        backend_policy=MediaMetadataBackendPolicy(primary="mutagen", fallbacks=["ffprobe"]),
        backends={"mutagen": mutagen, "ffprobe": ffprobe},
    )

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["artist", "track_title", "codec"],
        media_observation_demand=_media_demand(identity_keys=["artist", "track_title"], optional_keys=["codec"]),
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen"]
    assert {record["canonical_key"] for record in payload["observations"]} == {"metadata", "artist"}


def test_identity_missing_can_fall_back_to_available_identity_capable_backend(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
        supported_attributes=["codec", "metadata", "track_title", "artist"],
    )
    ffprobe = _FakeMediaBackend(
        "ffprobe",
        [RawMediaMetadataField(canonical_key="metadata", normalized_value={"TITLE": "Song"}, confidence=0.95, source_backend_id="ffprobe", raw_ref=str(sample))],
        supported_attributes=["track_title", "metadata"],
    )
    native = _FakeMediaBackend("native_minimal", supported_attributes=["codec", "container"])
    capability = MediaMetadataCapability(
        backend_policy=MediaMetadataBackendPolicy(primary="mutagen", fallbacks=["ffprobe", "native_minimal"]),
        backends={"mutagen": mutagen, "ffprobe": ffprobe, "native_minimal": native},
    )

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["track_title", "artist"],
        media_observation_demand=_media_demand(identity_keys=["track_title", "artist"]),
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == [str(sample)]
    assert native.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen", "ffprobe"]
    assert payload["media_metadata_capability"]["semantic_identity_evidence_counts"]["track_title"] == 1


def test_native_minimal_is_not_false_fallback_for_missing_identity(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
    )
    ffprobe = _FakeMediaBackend("ffprobe", error_code="FFPROBE_NOT_AVAILABLE", status="unavailable")
    native = _FakeMediaBackend(
        "native_minimal",
        [RawMediaMetadataField(canonical_key="container", normalized_value="m4a", confidence=0.8, source_backend_id="native_minimal", raw_ref=str(sample))],
        supported_attributes=["container", "codec", "bitrate", "sample_rate", "channels", "duration"],
    )
    capability = MediaMetadataCapability(backends={"mutagen": mutagen, "ffprobe": ffprobe, "native_minimal": native})

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["track_title", "artist"],
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == []
    assert native.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen"]
    assert payload["media_metadata_capability"]["semantic_identity_evidence_counts"] == {
        "track_title": 0,
        "artist": 0,
        "album": 0,
        "album_artist": 0,
    }


def test_ffprobe_may_execute_when_it_can_change_missing_identity_demand(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="codec", normalized_value="aac", confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
    )
    ffprobe = _FakeMediaBackend(
        "ffprobe",
        [RawMediaMetadataField(canonical_key="metadata", normalized_value={"ARTIST": "Artist"}, confidence=0.9, source_backend_id="ffprobe", raw_ref=str(sample))],
        supported_attributes=list(MEDIA_METADATA_EVIDENCE_KEYS),
    )
    native = _FakeMediaBackend("native_minimal", supported_attributes=["container", "codec", "bitrate", "sample_rate", "channels", "duration"])
    capability = MediaMetadataCapability(backends={"mutagen": mutagen, "ffprobe": ffprobe, "native_minimal": native})

    payload = capability.payload_for_boundary(
        file_path=str(sample),
        entity_ref={"entity_id": "entity_1"},
        requested_keys=["track_title", "artist"],
    )

    assert mutagen.calls == [str(sample)]
    assert ffprobe.calls == [str(sample)]
    assert native.calls == []
    assert payload["media_metadata_capability"]["attempted_backends"] == ["mutagen", "ffprobe"]
    assert payload["media_metadata_capability"]["semantic_identity_evidence_counts"]["artist"] == 1


def test_stage_local_backend_availability_snapshot_is_not_recomputed_per_entity(tmp_path: Path) -> None:
    sample = tmp_path / "sample.media"
    sample.write_bytes(b"semantic fixture")
    mutagen = _FakeMediaBackend(
        "mutagen",
        [RawMediaMetadataField(canonical_key="metadata", normalized_value={"ARTIST": "Artist"}, confidence=0.95, source_backend_id="mutagen", raw_ref=str(sample))],
    )
    ffprobe = _FakeMediaBackend("ffprobe", error_code="FFPROBE_NOT_AVAILABLE", status="unavailable")
    capability = MediaMetadataCapability(backends={"mutagen": mutagen, "ffprobe": ffprobe})
    snapshot = capability.backend_availability_snapshot()

    capability.payload_for_boundary(file_path=str(sample), entity_ref={"entity_id": "entity_1"}, requested_keys=["artist"], backend_availability_snapshot=snapshot)
    capability.payload_for_boundary(file_path=str(sample), entity_ref={"entity_id": "entity_2"}, requested_keys=["artist"], backend_availability_snapshot=snapshot)

    assert mutagen.descriptor_calls == 1
    assert ffprobe.descriptor_calls == 1


def test_mutagen_backend_reports_available_when_dependency_is_synced() -> None:
    backend = MutagenMediaMetadataBackend()

    descriptor = backend.descriptor()

    assert descriptor.dependency_name == "mutagen"
    assert descriptor.status == "available"
    assert descriptor.dependency_version
