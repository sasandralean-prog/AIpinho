from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.semantic_artifact_intent import ArtifactIntentPlan, SemanticEntitySelectionResult


class SemanticEntitySelectionService:
    """Selects observed entities for semantic artifact binding.

    The service operates only on an already compiled ObservedEntity graph. It
    does not inspect the filesystem and does not infer final media truth.
    """

    def select(
        self,
        *,
        graph: dict[str, Any],
        intent: ArtifactIntentPlan,
        max_entities: int,
    ) -> SemanticEntitySelectionResult:
        entities = [item for item in graph.get("entities") or [] if isinstance(item, dict)]
        max_rows = max(1, int(max_entities or 1))
        root_roles_seen = self._count_by_role(entities)
        eligible: list[dict[str, Any]] = []
        rejected_count = 0
        rejection_reasons: dict[str, int] = {}
        for entity in entities:
            reasons = self._rejection_reasons(entity, intent)
            if reasons:
                rejected_count += 1
                for reason in reasons:
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                continue
            eligible.append(entity)
        selected = self._prioritize(eligible, intent)[:max_rows]
        bound_rows = [self._row_binding(entity, intent) for entity in selected]
        bound_rows_with_evidence = [row for row in bound_rows if row["safe_to_use"]]
        evidence_refs = [
            ref
            for row in bound_rows
            for ref in row.get("evidence_refs", [])
            if ref
        ]
        semantic_gaps = self._semantic_gaps(
            intent=intent,
            total_eligible=len(eligible),
            selected=selected,
            bound_rows=bound_rows,
            rejection_reasons=rejection_reasons,
        )
        status = "selected" if bound_rows_with_evidence else "blocked"
        reason_code = None if bound_rows_with_evidence else intent.block_reason_if_missing
        limitations = []
        if len(eligible) > len(selected):
            limitations.append("semantic_entity_window_applied")
        if not bound_rows_with_evidence:
            limitations.append("semantic_entity_binding_insufficient")
        return SemanticEntitySelectionResult(
            artifact_intent_plan_id=intent.plan_id,
            status=status,
            reason_code=reason_code,
            expected_rows=len(eligible),
            selected_rows=len(selected),
            bound_rows=len(bound_rows_with_evidence),
            evidence_ref_count=len(list(dict.fromkeys(evidence_refs))),
            root_roles_seen=root_roles_seen,
            root_roles_selected=self._count_by_role(selected),
            selected_entity_ids=[str(item.get("entity_id") or "") for item in selected if item.get("entity_id")],
            rejected_count=rejected_count,
            rejection_reasons=rejection_reasons,
            limitations=limitations,
            semantic_gaps=semantic_gaps,
            rows=bound_rows,
            report={
                "artifact_kind": intent.artifact_kind,
                "semantic_domain": intent.semantic_domain,
                "resolution_sources": intent.resolution_sources,
                "required_root_roles": intent.source_root_roles_required,
                "required_entity_roles": intent.required_entity_roles,
                "max_entities": max_rows,
                "path_hint_authority": bool(intent.metadata.get("path_hint_authority")),
            },
        )

    def _rejection_reasons(self, entity: dict[str, Any], intent: ArtifactIntentPlan) -> list[str]:
        reasons: list[str] = []
        root_role = str(entity.get("source_root_role") or self._attribute_value(entity, "source_root_role") or "")
        entity_role = str(entity.get("entity_role") or self._attribute_value(entity, "entity_role") or "")
        entity_kind = str(entity.get("entity_kind") or "")
        evidence_refs = [str(item) for item in entity.get("evidence_refs") or [] if item]
        if intent.source_root_roles_required and root_role not in set(intent.source_root_roles_required):
            reasons.append("ROOT_ROLE_NOT_ALLOWED")
        if intent.required_entity_types and entity_kind not in set(intent.required_entity_types):
            reasons.append("ENTITY_TYPE_NOT_ALLOWED")
        if intent.required_entity_roles and entity_role and entity_role not in set(intent.required_entity_roles):
            reasons.append("ENTITY_ROLE_NOT_ALLOWED")
        eligibility = entity.get("selection_eligibility") if isinstance(entity.get("selection_eligibility"), dict) else {}
        if intent.artifact_kind == "media_corpus_inventory" and eligibility.get("corpus_inventory") is False:
            reasons.append("ENTITY_NOT_ELIGIBLE_FOR_CORPUS_INVENTORY")
        if not str(entity.get("entity_id") or ""):
            reasons.append("ENTITY_ID_MISSING")
        if not evidence_refs:
            reasons.append("ENTITY_EVIDENCE_REF_MISSING")
        return list(dict.fromkeys(reasons))

    def _prioritize(self, entities: list[dict[str, Any]], intent: ArtifactIntentPlan) -> list[dict[str, Any]]:
        def score(entity: dict[str, Any]) -> tuple[int, int, str]:
            observed = 0
            for attribute in intent.required_attributes:
                value = self._attribute_value(entity, attribute)
                if value not in (None, ""):
                    observed += 1
            evidence_count = len([item for item in entity.get("evidence_refs") or [] if item])
            return (observed, evidence_count, str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or ""))
        return sorted(entities, key=score, reverse=True)

    def _row_binding(self, entity: dict[str, Any], intent: ArtifactIntentPlan) -> dict[str, Any]:
        evidence_refs = [str(item) for item in entity.get("evidence_refs") or [] if item]
        unknown = []
        observed = {}
        for attribute in intent.required_attributes:
            value = self._attribute_value(entity, attribute)
            if value not in (None, ""):
                observed[attribute] = value
            else:
                unknown.append(attribute)
        limitations = []
        if "metadata_status" in intent.required_attributes:
            limitations.append("media_metadata_capability_not_configured")
        if unknown:
            limitations.append("required_attribute_limited")
        safe = bool(entity.get("entity_id") and entity.get("source_root_role") and evidence_refs)
        return {
            "row_id": f"row:{entity.get('entity_id')}",
            "entity_id": entity.get("entity_id"),
            "source_root_role": entity.get("source_root_role") or self._attribute_value(entity, "source_root_role"),
            "relative_path": entity.get("relative_path") or self._attribute_value(entity, "relative_path"),
            "observed_attributes": observed,
            "unknown_attributes": unknown,
            "not_configured_attributes": ["codec", "container", "bitrate", "sample_rate", "duration", "metadata"],
            "evidence_refs": evidence_refs,
            "limitations": list(dict.fromkeys(limitations)),
            "confidence": float(entity.get("confidence") or 1.0),
            "truth_eligible": False,
            "safe_to_use": safe,
        }

    def _semantic_gaps(
        self,
        *,
        intent: ArtifactIntentPlan,
        total_eligible: int,
        selected: list[dict[str, Any]],
        bound_rows: list[dict[str, Any]],
        rejection_reasons: dict[str, int],
    ) -> list[dict[str, Any]]:
        gaps: list[dict[str, Any]] = []
        if total_eligible == 0:
            gaps.append(
                {
                    "gap_type": "MEDIA_CORPUS_ENTITY_SELECTION_EMPTY",
                    "reason_code": intent.block_reason_if_missing,
                    "perception_domain": "entity_selection",
                    "severity": "high",
                    "expected": {
                        "root_roles": intent.source_root_roles_required,
                        "entity_roles": intent.required_entity_roles,
                    },
                    "observed": {"eligible_rows": 0, "rejection_reasons": rejection_reasons},
                    "confidence": 1.0,
                    "repair_hint": "Bind corpus/library observed entities before rendering the semantic inventory.",
                    "evidence_refs": [],
                }
            )
        if selected and not any(row.get("safe_to_use") for row in bound_rows):
            gaps.append(
                {
                    "gap_type": "ARTIFACT_EVIDENCE_BINDING_MISSING",
                    "reason_code": "ARTIFACT_EVIDENCE_BINDING_MISSING",
                    "perception_domain": "evidence_binding",
                    "severity": "high",
                    "expected": "entity_id/source_root_role/evidence_ref",
                    "observed": "row_binding_without_minimum_evidence",
                    "confidence": 1.0,
                    "repair_hint": "Rows require minimum evidence refs before they can be safe to use.",
                    "evidence_refs": [],
                }
            )
        return gaps

    def _attribute_value(self, entity: dict[str, Any], attribute: str) -> Any:
        canonical = {
            "filename": "name",
            "file_name": "name",
            "path": "relative_path",
            "evidence_ref": "evidence_refs",
        }.get(str(attribute), str(attribute))
        if canonical == "entity_id":
            return entity.get("entity_id")
        if canonical == "evidence_refs":
            refs = [str(item) for item in entity.get("evidence_refs") or [] if item]
            return refs[0] if refs else None
        if entity.get(canonical) not in (None, ""):
            return entity.get(canonical)
        observed = entity.get("observed_attributes") if isinstance(entity.get("observed_attributes"), dict) else {}
        item = observed.get(canonical)
        if isinstance(item, dict) and item.get("status") in {"observed", "inferred"}:
            return item.get("value")
        return None

    def _count_by_role(self, entities: list[dict[str, Any]]) -> dict[str, int]:
        rows: dict[str, int] = {}
        for entity in entities:
            role = str(entity.get("source_root_role") or self._attribute_value(entity, "source_root_role") or "unknown_root")
            rows[role] = rows.get(role, 0) + 1
        return rows
