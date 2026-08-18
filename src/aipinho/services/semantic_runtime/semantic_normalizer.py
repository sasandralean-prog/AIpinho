from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity, ISRMetadata
from aipinho.utils.yaml_loader import load_yaml_file


class SynonymResolver:
    def __init__(self, config: dict[str, Any]) -> None:
        raw = config.get("synonyms", {}) if isinstance(config.get("synonyms", {}), dict) else {}
        self.lookup: dict[str, str] = {}
        for canonical, values in raw.items():
            self.lookup[str(canonical).casefold()] = str(canonical)
            for value in values or []:
                self.lookup[str(value).casefold()] = str(canonical)

    def resolve(self, value: str) -> str:
        return self.lookup.get(str(value).casefold(), value)


class CanonicalIntentResolver:
    def __init__(self, config: dict[str, Any], synonyms: SynonymResolver) -> None:
        self.synonyms = synonyms
        self.intent_map = {str(key): str(value) for key, value in (config.get("intent_map", {}) or {}).items()}

    def resolve(self, intent: str) -> str:
        candidate = self.synonyms.resolve(intent)
        return self.intent_map.get(candidate, candidate)


class CanonicalScopeResolver:
    def __init__(self, config: dict[str, Any]) -> None:
        self.scope_map = {str(key).casefold(): str(value) for key, value in (config.get("scope_map", {}) or {}).items()}

    def resolve(self, scope: str) -> str:
        return self.scope_map.get(str(scope).casefold(), scope)


class CanonicalConstraintResolver:
    def __init__(self, config: dict[str, Any]) -> None:
        self.constraint_map = {str(key): str(value) for key, value in (config.get("constraint_map", {}) or {}).items()}

    def resolve(self, constraints: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key in sorted(constraints):
            canonical = self.constraint_map.get(str(key), str(key))
            value = constraints[key]
            if canonical in normalized:
                normalized[canonical] = bool(normalized[canonical]) or bool(value) if isinstance(value, bool) else value
            else:
                normalized[canonical] = value
        return normalized


class CanonicalOutputResolver:
    def __init__(self, config: dict[str, Any]) -> None:
        self.output_map = {str(key).casefold(): str(value) for key, value in (config.get("output_map", {}) or {}).items()}

    def resolve(self, outputs: list[str]) -> list[str]:
        normalized = {self.output_map.get(str(output).casefold(), str(output)) for output in outputs}
        return sorted(normalized)


class CanonicalPermissionResolver:
    def __init__(self, config: dict[str, Any]) -> None:
        self.permission_map = {str(key).casefold(): str(value) for key, value in (config.get("permission_map", {}) or {}).items()}

    def resolve(self, permissions: list[str]) -> list[str]:
        normalized = {self.permission_map.get(str(permission).casefold(), str(permission)) for permission in permissions}
        return sorted(normalized)


class SemanticNormalizer:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "semantic_runtime" / "semantic_normalizer.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.synonyms = SynonymResolver(self.config)
        self.intent_resolver = CanonicalIntentResolver(self.config, self.synonyms)
        self.scope_resolver = CanonicalScopeResolver(self.config)
        self.constraint_resolver = CanonicalConstraintResolver(self.config)
        self.output_resolver = CanonicalOutputResolver(self.config)
        self.permission_resolver = CanonicalPermissionResolver(self.config)

    def normalize(self, isr: IntermediateSemanticRepresentation) -> IntermediateSemanticRepresentation:
        normalized = IntermediateSemanticRepresentation(
            version=isr.version,
            status=isr.status,
            intent=self.intent_resolver.resolve(isr.intent),
            entities=self._normalize_entities(isr.entities),
            scope=self.scope_resolver.resolve(isr.scope),
            permissions_requested=self.permission_resolver.resolve(isr.permissions_requested),
            constraints=self.constraint_resolver.resolve(isr.constraints),
            expected_outputs=self.output_resolver.resolve(isr.expected_outputs),
            ambiguity=deepcopy(isr.ambiguity),
            confidence=isr.confidence,
            semantic_trace=[
                *isr.semantic_trace,
                {
                    "stage": "semantic_normalization",
                    "status": "ready",
                    "data": {
                        "source_intent": isr.intent,
                        "normalized_intent": self.intent_resolver.resolve(isr.intent),
                        "source_scope": isr.scope,
                        "normalized_scope": self.scope_resolver.resolve(isr.scope),
                    },
                },
            ],
            metadata=ISRMetadata(
                isr_id=isr.metadata.isr_id,
                schema_name=isr.metadata.schema_name,
                producer_role=isr.metadata.producer_role,
                capability_id=isr.metadata.capability_id,
                contract_id=isr.metadata.contract_id,
                session_id=isr.metadata.session_id,
                model_selection=deepcopy(isr.metadata.model_selection),
                created_at=isr.metadata.created_at,
            ),
            reasoning_summary=isr.reasoning_summary,
            warnings=list(isr.warnings),
            blocked_reasons=list(isr.blocked_reasons),
            effect_flags=deepcopy(isr.effect_flags),
            runtime_refs=deepcopy(isr.runtime_refs),
            extensions={**deepcopy(isr.extensions), "semantic_normalized": True},
        )
        return normalized

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "semantic_normalizer",
            "config": str(self.config_path),
        }

    def _normalize_entities(self, entities: list[ISREntity]) -> list[ISREntity]:
        normalized = [
            ISREntity(
                entity_type=str(entity.entity_type).casefold(),
                value=str(entity.value).strip(),
                confidence=entity.confidence,
                source=entity.source,
                metadata=deepcopy(entity.metadata),
            )
            for entity in entities
        ]
        return sorted(normalized, key=lambda item: (item.entity_type, item.value.casefold()))
