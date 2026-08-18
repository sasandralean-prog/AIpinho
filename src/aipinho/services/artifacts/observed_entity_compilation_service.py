from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.observed_entity import (
    CorpusDescriptor,
    EntityEvidenceGraph,
    ObservedEntity,
    ObservedEntityAttribute,
    RootBinding,
    RootBindingPolicyDecision,
    WorkspaceRootDescriptor,
)
from aipinho.utils.yaml_loader import load_yaml_file


class ObservedEntityCompilationService:
    """Compiles raw runtime evidence into reusable observed entity IR.

    The service does not render artifacts and does not validate completion. It
    only turns observed facts into an entity graph that artifact renderers and
    semantic validators can consume without reinterpreting raw evidence.
    """

    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "artifacts" / "observed_entity_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )
        self.attribute_aliases = self._compile_aliases(self.policy.get("attribute_aliases"))

    def compile(
        self,
        *,
        workspace: str,
        workspace_context: dict[str, Any] | None = None,
        analysis_payload: dict[str, Any] | None = None,
        dependency_check: dict[str, Any] | None = None,
    ) -> EntityEvidenceGraph:
        context = workspace_context if isinstance(workspace_context, dict) else {}
        payload = analysis_payload if isinstance(analysis_payload, dict) else {}
        gaps: list[dict[str, Any]] = []
        entities: list[ObservedEntity] = []
        roots = self._root_descriptors(workspace=workspace, workspace_context=context)
        root_bindings = self._root_bindings(roots)
        binding_by_root_id = {item.root_id: item for item in root_bindings}
        ordered_roots = self._ordered_root_descriptors(roots)
        max_entities = self._max_entities()
        for index, descriptor in enumerate(ordered_roots):
            binding = binding_by_root_id.get(descriptor.root_id)
            if binding is not None and not binding.observation_allowed:
                gaps.append(
                    self._gap(
                        "CORPUS_ROOT_POLICY_BLOCKED" if descriptor.role in {"library_root", "corpus_root"} else "ROOT_OBSERVATION_POLICY_BLOCKED",
                        expected=f"observation_allowed_for:{descriptor.role}",
                        observed=binding.policy_decision.policy_status,
                        evidence_refs=binding.evidence_refs,
                    )
                )
                continue
            remaining_capacity = max_entities - len(entities)
            if remaining_capacity <= 0:
                gaps.append(
                    self._gap(
                        "ENTITY_CARDINALITY_TRUNCATED",
                        expected="all_observed_entity_roots",
                        observed=len(entities),
                        evidence_refs=[item.path for item in ordered_roots[index:]],
                    )
                )
                break
            root = Path(descriptor.path)
            root_limit = self._root_scan_limit(
                remaining_capacity=remaining_capacity,
                remaining_root_count=max(1, len(ordered_roots) - index),
            )
            before_count = len(entities)
            root_entities = self._file_entities(root, descriptor=descriptor, gaps=gaps, max_entities=root_limit)
            entities.extend(root_entities)
            if len(root_entities) >= root_limit:
                gaps.append(
                    self._gap(
                        "ENTITY_CARDINALITY_TRUNCATED",
                        expected=f"all_observed_entities_for:{descriptor.role}",
                        observed=len(root_entities),
                        evidence_refs=[str(root)],
                    )
                )
            if len(entities) == before_count and descriptor.role in {"library_root", "corpus_root"}:
                gaps.append(
                    self._gap(
                        "CORPUS_ROOT_ENTITY_SELECTION_EMPTY",
                        expected=f"observed_entities_for:{descriptor.role}",
                        observed=0,
                        evidence_refs=[str(root)],
                    )
                )
        entities.extend(self._finding_entities(payload))
        if not entities:
            gaps.append(self._gap("ENTITY_NOT_OBSERVED", expected="one_or_more_observed_entities", observed=0))
        if dependency_check and isinstance(dependency_check.get("artifacts"), list):
            entities.extend(self._artifact_reference_entities(dependency_check))
        entities = entities[: self._max_entities()]
        return EntityEvidenceGraph(
            source="runtime_evidence",
            root_descriptors=roots,
            root_bindings=root_bindings,
            corpus_descriptors=[
                CorpusDescriptor(root_id=item.root_id, path=item.path, role="corpus_root", source=item.source)
                for item in roots
                if item.role in {"library_root", "corpus_root"}
            ],
            roots_scanned_by_role=self._roots_scanned_by_role(roots),
            entities_by_root_role=self._entities_by_root_role(entities),
            entities=entities,
            semantic_gaps=gaps,
        )

    def value_for_field(self, entity: dict[str, Any], field: str) -> tuple[Any | None, bool]:
        canonical = self.canonical_attribute_name(field)
        observed = entity.get("observed_attributes") if isinstance(entity.get("observed_attributes"), dict) else {}
        inferred = entity.get("inferred_attributes") if isinstance(entity.get("inferred_attributes"), dict) else {}
        for container in (observed, inferred):
            item = container.get(canonical)
            if isinstance(item, dict) and item.get("status") in {"observed", "inferred"}:
                return item.get("value"), True
        return None, False

    def canonical_attribute_name(self, field: str) -> str:
        normalized = self._normalize(field)
        for canonical, aliases in self.attribute_aliases.items():
            if normalized == canonical or normalized in aliases:
                return canonical
        compact = self._compact(normalized)
        for canonical, aliases in self.attribute_aliases.items():
            candidates = [canonical, *aliases]
            if any(self._compact(candidate) == compact for candidate in candidates):
                return canonical
            if any(self._near_compact_match(compact, self._compact(candidate)) for candidate in candidates):
                return canonical
        return normalized

    def select_entities_for_schema(self, graph: dict[str, Any], schema: list[str]) -> list[dict[str, Any]]:
        entities = [item for item in graph.get("entities") or [] if isinstance(item, dict)]
        if not entities or not schema:
            return []
        scores_by_kind: dict[str, int] = {}
        for entity in entities:
            kind = str(entity.get("entity_kind") or "")
            score = sum(1 for field in schema if self.value_for_field(entity, field)[1])
            scores_by_kind[kind] = scores_by_kind.get(kind, 0) + score
        if not scores_by_kind:
            return entities
        selected_kind = max(scores_by_kind, key=lambda key: (scores_by_kind[key], key))
        if scores_by_kind[selected_kind] <= 0:
            return entities
        return [entity for entity in entities if str(entity.get("entity_kind") or "") == selected_kind]

    def schema_coverage(self, entities: list[dict[str, Any]], schema: list[str]) -> dict[str, Any]:
        if not schema:
            return {"status": "not_applicable", "covered_fields": [], "missing_fields": []}
        covered = []
        missing = []
        for field in schema:
            if any(self.value_for_field(entity, field)[1] for entity in entities):
                covered.append(field)
            else:
                missing.append(field)
        ratio = 1.0 if not schema else len(covered) / max(1, len(schema))
        return {
            "status": "complete" if not missing else "partial",
            "coverage_ratio": ratio,
            "covered_fields": covered,
            "missing_fields": missing,
        }

    def _root_descriptors(self, *, workspace: str, workspace_context: dict[str, Any]) -> list[WorkspaceRootDescriptor]:
        policy = self._root_role_policy()
        raw_roots: list[tuple[str, str, str]] = [(workspace, "workspace", policy.get("project_root_role", "project_root"))]
        project_root = str(workspace_context.get("project_root") or "")
        if project_root:
            raw_roots.append((project_root, "project_root", policy.get("project_root_role", "project_root")))
        for raw in self._string_list(workspace_context.get("external_roots")):
            raw_roots.append((raw, "external_roots", policy.get("external_root_role", "external_root")))
        for raw in self._string_list(workspace_context.get("library_roots")):
            raw_roots.append((raw, "library_roots", policy.get("library_root_role", "library_root")))
        descriptors: list[WorkspaceRootDescriptor] = []
        seen: dict[str, int] = {}
        for raw, source, role in raw_roots:
            try:
                path = Path(str(raw)).expanduser().resolve(strict=False)
            except Exception:
                continue
            key = str(path).casefold()
            evidence_ref = f"root_binding:{self._stable_id('root', str(path), role)}"
            policy_decision = self._root_policy_decision(
                root_id=self._stable_id("root", str(path), role),
                path=path,
                role=role,
                source=source,
                workspace_context=workspace_context,
            )
            descriptor = WorkspaceRootDescriptor(
                root_id=policy_decision.root_id,
                path=str(path),
                role=role,
                source=source,
                purposes=["corpus"] if role in {"library_root", "corpus_root"} else ["project"] if role == "project_root" else [],
                policy_status=policy_decision.policy_status,
                access_scope=policy_decision.access_scope,
                observation_allowed=policy_decision.observation_allowed,
                mutation_allowed=policy_decision.mutation_allowed,
                policy_reason_codes=policy_decision.reason_codes,
                evidence_refs=[evidence_ref],
            )
            if key in seen:
                index = seen[key]
                existing = descriptors[index]
                if self._root_role_priority(descriptor.role) > self._root_role_priority(existing.role):
                    merged_sources = ",".join(dict.fromkeys([*existing.source.split(","), source]))
                    descriptors[index] = descriptor.model_copy(update={"source": merged_sources})
                continue
            seen[key] = len(descriptors)
            descriptors.append(descriptor)
        return descriptors

    def _root_bindings(self, descriptors: list[WorkspaceRootDescriptor]) -> list[RootBinding]:
        bindings: list[RootBinding] = []
        for descriptor in descriptors:
            decision = RootBindingPolicyDecision(
                root_id=descriptor.root_id,
                policy_status=descriptor.policy_status,
                observation_allowed=descriptor.observation_allowed,
                mutation_allowed=descriptor.mutation_allowed,
                access_scope=list(descriptor.access_scope),
                reason_codes=list(descriptor.policy_reason_codes),
            )
            bindings.append(
                RootBinding(
                    root_id=descriptor.root_id,
                    path=descriptor.path,
                    role=descriptor.role,
                    source=descriptor.source,
                    purposes=list(descriptor.purposes),
                    provenance={
                        "source": descriptor.source,
                        "role_assignment": "workspace_context_root_role",
                        "path_authority": False,
                    },
                    evidence_refs=list(descriptor.evidence_refs),
                    policy_decision=decision,
                    observation_allowed=decision.observation_allowed,
                    mutation_allowed=decision.mutation_allowed,
                )
            )
        return bindings

    def _root_policy_decision(
        self,
        *,
        root_id: str,
        path: Path,
        role: str,
        source: str,
        workspace_context: dict[str, Any],
    ) -> RootBindingPolicyDecision:
        readonly_flags = workspace_context.get("readonly_flags") if isinstance(workspace_context.get("readonly_flags"), dict) else {}
        readonly_declared = bool(readonly_flags.get(str(path), True))
        reason_codes: list[str] = []
        if not readonly_declared:
            reason_codes.append("ROOT_OBSERVATION_NOT_READONLY_DECLARED")
        if role == "unknown_root":
            reason_codes.append("ROOT_ROLE_UNKNOWN")
        if not path.exists():
            reason_codes.append("ROOT_PATH_NOT_OBSERVED")
        observation_allowed = readonly_declared and role != "unknown_root" and path.exists()
        if role in {"library_root", "corpus_root"} and not observation_allowed:
            reason_codes.append("CORPUS_ROOT_POLICY_BLOCKED")
        policy_status = "allowed" if observation_allowed else "blocked"
        access_scope = ["read_metadata", "list_files"] if observation_allowed else []
        return RootBindingPolicyDecision(
            root_id=root_id,
            policy_status=policy_status,
            observation_allowed=observation_allowed,
            mutation_allowed=False,
            access_scope=access_scope,
            reason_codes=list(dict.fromkeys(reason_codes or ["ROOT_OBSERVATION_READONLY_ALLOWED"])),
        )

    def _root_role_priority(self, role: str) -> int:
        return {
            "unknown_root": 0,
            "external_root": 10,
            "artifact_root": 15,
            "project_root": 20,
            "source_code_root": 25,
            "library_root": 30,
            "corpus_root": 35,
        }.get(str(role), 5)

    def _ordered_root_descriptors(self, descriptors: list[WorkspaceRootDescriptor]) -> list[WorkspaceRootDescriptor]:
        return sorted(
            descriptors,
            key=lambda descriptor: (
                self._root_role_priority(descriptor.role),
                -len(str(descriptor.path)),
                str(descriptor.path).casefold(),
            ),
            reverse=True,
        )

    def _root_scan_limit(self, *, remaining_capacity: int, remaining_root_count: int) -> int:
        scan = self.policy.get("scan") if isinstance(self.policy.get("scan"), dict) else {}
        configured = int(scan.get("max_entities_per_root") or 0)
        if configured > 0:
            return max(1, min(remaining_capacity, configured))
        fair_share = max(1, remaining_capacity // max(1, remaining_root_count))
        return max(1, min(remaining_capacity, fair_share))

    def _file_entities(
        self,
        root: Path,
        *,
        descriptor: WorkspaceRootDescriptor,
        gaps: list[dict[str, Any]],
        max_entities: int | None = None,
    ) -> list[ObservedEntity]:
        if not root.exists():
            gaps.append(
                self._gap(
                    "ENTITY_SOURCE_NOT_OBSERVED",
                    expected=str(root),
                    observed="source_missing",
                    evidence_refs=[str(root)],
                )
            )
            return []
        if root.is_file():
            return [self._file_entity(root, source_root=root.parent, root_role=descriptor.role)]
        entities: list[ObservedEntity] = []
        max_depth = self._max_depth()
        limit = max(1, int(max_entities or self._max_entities()))
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            try:
                depth = len(current_path.relative_to(root).parts)
            except ValueError:
                depth = 0
            if depth >= max_depth:
                dirs[:] = []
            for filename in files:
                entities.append(self._file_entity(current_path / filename, source_root=root, root_role=descriptor.role))
                if len(entities) >= limit:
                    return entities
        return entities

    def _file_entity(self, path: Path, *, source_root: Path, root_role: str) -> ObservedEntity:
        try:
            stat = path.stat()
        except OSError:
            stat = None
        try:
            relative_path = str(path.relative_to(source_root))
        except ValueError:
            relative_path = str(path)
        evidence_ref = f"file:{path}"
        attributes = {
            "name": self._attribute("name", path.name, evidence_ref),
            "extension": self._attribute("extension", path.suffix.lstrip(".").casefold(), evidence_ref),
            "relative_path": self._attribute("relative_path", relative_path, evidence_ref),
            "source_root": self._attribute("source_root", str(source_root), evidence_ref),
            "source_root_role": self._attribute("source_root_role", root_role, evidence_ref),
        }
        entity_role = self._entity_role(relative_path=relative_path, source_root_role=root_role)
        attributes["entity_role"] = self._attribute("entity_role", entity_role, evidence_ref)
        if stat is not None:
            attributes["size_bytes"] = self._attribute("size_bytes", stat.st_size, evidence_ref)
        return ObservedEntity(
            entity_id=self._stable_id("file", str(path)),
            entity_kind="file",
            source=str(source_root),
            source_root=str(source_root),
            source_root_role=root_role,
            relative_path=relative_path,
            entity_role=entity_role,
            entity_domain_hypotheses=self._entity_domain_hypotheses(source_root_role=root_role, entity_role=entity_role),
            selection_eligibility=self._selection_eligibility(source_root_role=root_role, entity_role=entity_role),
            exclusion_reasons=self._entity_exclusion_reasons(entity_role=entity_role),
            observed_attributes=attributes,
            evidence_refs=[evidence_ref],
        )

    def _finding_entities(self, payload: dict[str, Any]) -> list[ObservedEntity]:
        rows = payload.get("findings") if isinstance(payload.get("findings"), list) else []
        entities: list[ObservedEntity] = []
        for index, item in enumerate(row for row in rows if isinstance(row, dict)):
            evidence_refs = [str(value) for value in item.get("evidence_paths") or [] if value]
            fallback_ref = f"analysis_finding:{index}"
            attributes = {}
            for name in ("severity", "title", "summary"):
                value = item.get(name)
                if value not in (None, ""):
                    attributes[name] = self._attribute(name, value, evidence_refs[0] if evidence_refs else fallback_ref)
            entities.append(
                ObservedEntity(
                    entity_id=self._stable_id("finding", str(index), str(item.get("title") or "")),
                    entity_kind="finding",
                    source="project_analysis",
                    observed_attributes=attributes,
                    evidence_refs=evidence_refs or [fallback_ref],
                )
            )
        return entities

    def _artifact_reference_entities(self, dependency_check: dict[str, Any]) -> list[ObservedEntity]:
        rows = dependency_check.get("artifacts") if isinstance(dependency_check.get("artifacts"), list) else []
        entities: list[ObservedEntity] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            artifact_id = str(item.get("artifact_id") or "")
            logical_path = str(item.get("logical_path") or "")
            evidence_ref = f"artifact:{artifact_id or logical_path}"
            attributes = {}
            if artifact_id:
                attributes["artifact_id"] = self._attribute("artifact_id", artifact_id, evidence_ref)
            if logical_path:
                attributes["relative_path"] = self._attribute("relative_path", logical_path, evidence_ref)
            entities.append(
                ObservedEntity(
                    entity_id=self._stable_id("artifact_reference", artifact_id, logical_path),
                    entity_kind="artifact_reference",
                    source="phase_dependency",
                    observed_attributes=attributes,
                    evidence_refs=[evidence_ref],
                )
            )
        return entities

    def _attribute(self, name: str, value: Any, evidence_ref: str) -> ObservedEntityAttribute:
        return ObservedEntityAttribute(name=name, value=value, status="observed", evidence_refs=[evidence_ref])

    def _gap(
        self,
        gap_type: str,
        *,
        expected: Any,
        observed: Any,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "gap_type": gap_type,
            "severity": "high",
            "expected": expected,
            "observed": observed,
            "confidence": 1.0,
            "repair_hint": "Collect or compile sufficient entity evidence before rendering the governed artifact.",
            "evidence_refs": evidence_refs or [],
        }

    def _root_role_policy(self) -> dict[str, Any]:
        return self.policy.get("root_role_policy") if isinstance(self.policy.get("root_role_policy"), dict) else {}

    def _entity_role(self, *, relative_path: str, source_root_role: str) -> str:
        if source_root_role in {"library_root", "corpus_root"}:
            return "corpus_file"
        first = self._first_segment(relative_path)
        policy = self._root_role_policy()
        if first in {self._normalize(item) for item in policy.get("cache_segments") or []}:
            return "cache_file"
        if first in {self._normalize(item) for item in policy.get("build_output_segments") or []}:
            return "build_output_file"
        if first in {self._normalize(item) for item in policy.get("generated_segments") or []}:
            return "generated_file"
        if first in {self._normalize(item) for item in policy.get("source_segments") or []}:
            return "project_source_file"
        if source_root_role == "project_root":
            return "project_file"
        if source_root_role == "external_root":
            return "external_file"
        return "file"

    def _entity_domain_hypotheses(self, *, source_root_role: str, entity_role: str) -> list[dict[str, Any]]:
        if source_root_role in {"library_root", "corpus_root"}:
            return [{"domain": "corpus_member", "confidence": 1.0, "reason": "source_root_role"}]
        if entity_role in {"project_source_file", "project_file"}:
            return [{"domain": "project_member", "confidence": 1.0, "reason": "source_root_role"}]
        if entity_role in {"build_output_file", "cache_file", "generated_file"}:
            return [{"domain": "project_derived_artifact", "confidence": 1.0, "reason": "entity_role"}]
        return [{"domain": "unknown_file", "confidence": 0.5, "reason": "fallback"}]

    def _selection_eligibility(self, *, source_root_role: str, entity_role: str) -> dict[str, Any]:
        policy = self._root_role_policy()
        corpus_roles = set(policy.get("corpus_preferred_root_roles") or ["library_root", "corpus_root"])
        corpus_excluded = set(policy.get("corpus_excluded_entity_roles") or [])
        return {
            "corpus_inventory": source_root_role in corpus_roles and entity_role not in corpus_excluded,
            "project_inventory": source_root_role == "project_root" and entity_role not in {"build_output_file", "cache_file"},
            "generic_collection": entity_role not in {"cache_file"},
        }

    def _entity_exclusion_reasons(self, *, entity_role: str) -> list[str]:
        reasons: list[str] = []
        if entity_role == "cache_file":
            reasons.append("CACHE_ROOT_OR_SEGMENT")
        if entity_role == "build_output_file":
            reasons.append("BUILD_OUTPUT_ROOT_OR_SEGMENT")
        if entity_role == "generated_file":
            reasons.append("GENERATED_ROOT_OR_SEGMENT")
        if entity_role == "project_source_file":
            reasons.append("PROJECT_SOURCE_ROOT_OR_SEGMENT")
        return reasons

    def _first_segment(self, relative_path: str) -> str:
        parts = Path(str(relative_path)).parts
        return self._normalize(parts[0]) if parts else ""

    def _roots_scanned_by_role(self, descriptors: list[WorkspaceRootDescriptor]) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for item in descriptors:
            rows.setdefault(item.role, []).append(item.path)
        return rows

    def _entities_by_root_role(self, entities: list[ObservedEntity]) -> dict[str, int]:
        rows: dict[str, int] = {}
        for entity in entities:
            role = entity.source_root_role or "unknown_root"
            rows[role] = rows.get(role, 0) + 1
        return rows

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _compile_aliases(self, raw: Any) -> dict[str, set[str]]:
        aliases: dict[str, set[str]] = {}
        if not isinstance(raw, dict):
            return aliases
        for canonical, values in raw.items():
            canonical_name = self._normalize(canonical)
            rows = values if isinstance(values, list) else [values]
            aliases[canonical_name] = {self._normalize(item) for item in rows if str(item).strip()}
        return aliases

    def _normalize(self, value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^0-9A-Za-z]+", "_", normalized.casefold())
        return "_".join(part for part in normalized.split("_") if part)

    def _compact(self, value: Any) -> str:
        return re.sub(r"[^0-9a-z]+", "", self._normalize(value))

    def _near_compact_match(self, value: str, candidate: str) -> bool:
        if not value or not candidate:
            return False
        limit = 2 if min(len(value), len(candidate)) >= 5 else 1
        if abs(len(value) - len(candidate)) > limit:
            return False
        return self._edit_distance(value, candidate, limit=limit) <= limit

    def _edit_distance(self, left: str, right: str, *, limit: int) -> int:
        previous = list(range(len(right) + 1))
        for index, left_char in enumerate(left, start=1):
            current = [index]
            row_min = index
            for right_index, right_char in enumerate(right, start=1):
                cost = 0 if left_char == right_char else 1
                value = min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + cost,
                )
                current.append(value)
                row_min = min(row_min, value)
            if row_min > limit:
                return row_min
            previous = current
        return previous[-1]

    def _stable_id(self, *parts: str) -> str:
        digest = hashlib.sha256("::".join(parts).encode("utf-8", errors="replace")).hexdigest()[:24]
        return f"observed_entity_{digest}"

    def _max_entities(self) -> int:
        scan = self.policy.get("scan") if isinstance(self.policy.get("scan"), dict) else {}
        return max(1, int(scan.get("max_entities") or 1))

    def _max_depth(self) -> int:
        scan = self.policy.get("scan") if isinstance(self.policy.get("scan"), dict) else {}
        return max(0, int(scan.get("max_depth") or 0))

    def _entity_limit_reached(self, entities: list[Any]) -> bool:
        return len(entities) >= self._max_entities()
