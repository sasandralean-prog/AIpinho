from __future__ import annotations

import re
import unicodedata
from typing import Any

from aipinho.schemas.artifacts.semantic_artifact_intent import ArtifactIntentPlan


class SemanticArtifactIntentResolver:
    """Resolves artifact intent from contract, prompt meaning, and workspace roles.

    This service does not observe files and does not render artifacts. Logical
    paths are weak hints; declared contracts and semantic request context carry
    the authority.
    """

    _INVENTORY_TERMS = {
        "inventory",
        "inventario",
        "catalog",
        "catalogo",
        "listar",
        "list",
        "mapear",
        "inventoryar",
        "inventariar",
    }
    _MEDIA_TERMS = {
        "media",
        "audio",
        "music",
        "musica",
        "musicas",
        "musical",
        "track",
        "tracks",
        "faixa",
        "faixas",
        "album",
        "codec",
        "bitrate",
        "sample",
        "metadata",
    }
    _CORPUS_TERMS = {
        "library",
        "biblioteca",
        "corpus",
        "collection",
        "colecao",
        "dataset",
    }

    def resolve(
        self,
        *,
        prompt: str | None = None,
        declared_contract: dict[str, Any] | None = None,
        workspace_context: dict[str, Any] | None = None,
        artifact_logical_path: str | None = None,
        known_phase_context: dict[str, Any] | None = None,
    ) -> ArtifactIntentPlan:
        contract = declared_contract if isinstance(declared_contract, dict) else {}
        context = workspace_context if isinstance(workspace_context, dict) else {}
        normalized_prompt = self._tokens(prompt)
        normalized_path = self._tokens(artifact_logical_path)
        contract_id = str(contract.get("contract_id") or "")
        expected_semantics = contract.get("expected_semantics") if isinstance(contract.get("expected_semantics"), dict) else {}
        schema = [str(item) for item in contract.get("canonical_schema") or contract.get("expected_schema") or [] if str(item).strip()]
        has_corpus_root = bool(context.get("library_roots") or context.get("corpus_roots"))
        contract_requests_media_inventory = (
            contract_id == "media_corpus_inventory_artifact"
            or bool(expected_semantics.get("media_corpus_inventory_required"))
        )
        prompt_requests_media_inventory = bool(
            normalized_prompt & self._INVENTORY_TERMS
            and normalized_prompt & self._MEDIA_TERMS
            and (has_corpus_root or normalized_prompt & self._CORPUS_TERMS)
        )
        path_hint = bool(normalized_path & self._INVENTORY_TERMS and normalized_path & self._MEDIA_TERMS)
        if contract_requests_media_inventory or prompt_requests_media_inventory:
            sources = []
            if contract_requests_media_inventory:
                sources.append("artifact_semantic_contract")
            if prompt_requests_media_inventory:
                sources.append("prompt_semantics")
            if has_corpus_root:
                sources.append("workspace_root_roles")
            if path_hint:
                sources.append("logical_path_hint")
            required = self._ordered(
                [
                    "entity_id",
                    "source_root_role",
                    "relative_path",
                    "name",
                    "extension",
                    "media_type",
                    "metadata_status",
                    "evidence_ref",
                    "limitations",
                    "validation_status",
                ]
            )
            optional = self._ordered(
                [
                    "track_title",
                    "artist",
                    "album",
                    "duration",
                    "codec",
                    "container",
                    "bitrate",
                    "sample_rate",
                    "channels",
                    "artwork",
                    "metadata",
                    "observations",
                    "relationship_candidate_refs",
                ]
            )
            return ArtifactIntentPlan(
                artifact_kind="media_corpus_inventory",
                semantic_domain="media_corpus",
                target_subject="media_corpus_entities",
                source_root_roles_required=["library_root", "corpus_root"],
                required_entity_types=["file"],
                required_entity_roles=["corpus_file", "media_asset_candidate"],
                required_attributes=[item for item in required if item in set(required + schema)],
                optional_attributes=[item for item in optional if item in set(optional + schema)],
                required_relationship_families=[],
                required_evidence_types=[
                    "entity_identity",
                    "root_role",
                    "source_path",
                    "observation_provenance",
                ],
                allowed_absence_states=["unknown", "not_observed", "not_configured", "unsupported", "blocked"],
                minimum_semantic_rows=1,
                partial_allowed=True,
                block_reason_if_missing="MUSIC_INVENTORY_ENTITY_BINDING_INSUFFICIENT",
                resolution_confidence=0.95 if contract_requests_media_inventory else 0.72,
                resolution_sources=sources,
                limitations=[] if contract_requests_media_inventory or prompt_requests_media_inventory else ["semantic_intent_low_confidence"],
                metadata={
                    "contract_id": contract_id or None,
                    "path_hint_used": path_hint,
                    "path_hint_authority": False,
                    "phase": (known_phase_context or {}).get("phase"),
                },
            )
        return ArtifactIntentPlan(
            artifact_kind=str(contract.get("artifact_kind") or contract.get("expected_kind") or "generic_artifact"),
            semantic_domain="generic",
            target_subject=None,
            source_root_roles_required=[],
            required_entity_types=[],
            required_entity_roles=[],
            required_attributes=schema,
            optional_attributes=[],
            required_evidence_types=[],
            allowed_absence_states=["unknown", "not_observed"],
            minimum_semantic_rows=0,
            partial_allowed=False,
            block_reason_if_missing="ARTIFACT_SEMANTIC_BINDING_INSUFFICIENT",
            resolution_confidence=0.35,
            resolution_sources=["default_generic_artifact"],
            metadata={"contract_id": contract_id or None},
        )

    def _tokens(self, value: Any) -> set[str]:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        return {item for item in re.split(r"[^0-9A-Za-z]+", normalized.casefold()) if item}

    def _ordered(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
