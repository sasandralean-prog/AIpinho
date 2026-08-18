from __future__ import annotations

import csv
import base64
import io
import json
import re
import zipfile
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_semantic_profile import (
    ArtifactSemanticGap,
    ArtifactSemanticProfile,
    SemanticComparison,
)
from aipinho.services.artifacts.relationship_validation_policy_service import RelationshipValidationPolicyService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ArtifactSemanticContractValidation:
    status: str
    contract_id: str | None = None
    missing_requirements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    profile: ArtifactSemanticProfile | None = None

    @property
    def passed(self) -> bool:
        return self.status == "passed"


class ArtifactSemanticContractService:
    """Compiles and validates artifact semantic profiles.

    This remains the single artifact semantic contract boundary. It observes the
    artifact material state, compiles expectations from declared contracts, and
    compares expected semantics with the observed artifact without mutating the
    artifact or taking over Completion/Speaker Truth authority.
    """

    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "artifacts" / "artifact_semantic_contract_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )
        self.relationship_validation = RelationshipValidationPolicyService()

    def validate(
        self,
        *,
        logical_path: str,
        content: str,
        content_type: str | None = None,
        declared_contract: dict[str, Any] | None = None,
    ) -> ArtifactSemanticContractValidation:
        content_bytes = self._content_bytes_for_validation(content, content_type)
        profile = self.profile(
            logical_path=logical_path,
            content_bytes=content_bytes,
            content_type=content_type,
            declared_contract=declared_contract,
        )
        return self._validation_from_profile(profile)

    def _content_bytes_for_validation(self, content: str, content_type: str | None) -> bytes:
        text = str(content or "")
        if str(content_type or "").lower() in {"application/zip", "application/x-zip-compressed"}:
            try:
                return base64.b64decode(text.encode("ascii"), validate=True)
            except Exception:
                return text.encode("utf-8")
        return text.encode("utf-8")

    def validate_artifact(self, artifact: dict[str, Any]) -> ArtifactSemanticContractValidation:
        profile = self.profile_for_artifact(artifact)
        return self._validation_from_profile(profile)

    def profile_for_artifact(self, artifact: dict[str, Any]) -> ArtifactSemanticProfile:
        logical_path = str(
            artifact.get("logical_path")
            or (artifact.get("metadata") or {}).get("logical_path")
            or (artifact.get("provenance") or {}).get("logical_path")
            or artifact.get("filename")
            or ""
        )
        path = self._artifact_path(artifact)
        content_bytes = b""
        if path is not None and path.exists() and path.is_file():
            try:
                content_bytes = path.read_bytes()
            except Exception:
                content_bytes = b""
        metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
        provenance = artifact.get("provenance") if isinstance(artifact.get("provenance"), dict) else {}
        declared_contract = (
            metadata.get("declared_contract")
            if isinstance(metadata.get("declared_contract"), dict)
            else provenance.get("declared_contract") if isinstance(provenance.get("declared_contract"), dict) else None
        )
        return self.profile(
            logical_path=logical_path,
            content_bytes=content_bytes,
            content_type=str(artifact.get("content_type") or ""),
            artifact_id=str(artifact.get("artifact_id") or ""),
            artifact_type=str(artifact.get("artifact_type") or ""),
            artifact_path=str(path) if path is not None else None,
            declared_contract=declared_contract,
        )

    def profile(
        self,
        *,
        logical_path: str,
        content_bytes: bytes,
        content_type: str | None = None,
        artifact_id: str | None = None,
        artifact_type: str | None = None,
        artifact_path: str | None = None,
        declared_contract: dict[str, Any] | None = None,
    ) -> ArtifactSemanticProfile:
        compiled_contract = self.compile_contract(
            logical_path=logical_path,
            content_type=content_type,
            declared_contract=declared_contract,
        )
        observed = self._observe(content_bytes, content_type=content_type, logical_path=logical_path)
        bound_observations = self._bound_attribute_observations(compiled_contract)
        bound_relationship_observations = self._bound_relationship_observations(compiled_contract)
        relationship_provenance_traces = self._relationship_provenance_traces(compiled_contract)
        relationship_evidence_records = self._relationship_evidence_records(compiled_contract)
        relationship_validation_results = self.relationship_validation.validate_many(
            relationship_observations=bound_relationship_observations,
            provenance_traces=relationship_provenance_traces,
            evidence_records=relationship_evidence_records,
            policy=compiled_contract.get("relationship_validation_policy")
            if isinstance(compiled_contract.get("relationship_validation_policy"), dict)
            else None,
        )
        relationship_validation_summary = self.relationship_validation.summary(relationship_validation_results)
        relationship_rendered_fields = self._relationship_rendered_fields(
            compiled_contract,
            bound_relationship_observations,
            relationship_provenance_traces,
            relationship_validation_summary,
        )
        relationship_rendering_summary = self._relationship_rendering_summary(
            relationship_rendered_fields,
            bound_relationship_observations,
            relationship_provenance_traces,
            relationship_validation_summary,
        )
        bound_keys = self._bound_observed_keys(compiled_contract, bound_observations)
        bound_evidence_refs = self._bound_evidence_refs(bound_observations)
        if bound_observations:
            observed.setdefault("semantics", {})["bound_attribute_observation_count"] = len(bound_observations)
            observed.setdefault("semantics", {})["observed_attributes"] = sorted(bound_keys)
            observed.setdefault("semantics", {})["observed_attribute_counts"] = self._count_by_key(bound_observations, "canonical_key")
            observed.setdefault("evidence", [])
            observed["evidence"] = list(dict.fromkeys([*observed.get("evidence", []), *bound_evidence_refs[:50]]))
        if bound_relationship_observations:
            observed.setdefault("semantics", {})["bound_relationship_observation_count"] = len(bound_relationship_observations)
            observed.setdefault("semantics", {})["relationship_truth_eligible"] = False
            observed.setdefault("semantics", {})["relationship_rendered_field_count"] = relationship_rendering_summary.get("rendered_field_count", 0)
        structural_gaps = self._structural_gaps(content_bytes)
        material_gaps = self._material_gaps(compiled_contract, observed)
        contract_gaps = self._contract_gaps(compiled_contract, observed, content_bytes)
        semantic_gaps = self._semantic_gaps(compiled_contract, observed, bound_keys=bound_keys)
        relationship_gaps = self._relationship_gaps(
            compiled_contract,
            bound_relationship_observations,
            relationship_validation_summary,
        )
        semantic_gaps.extend(relationship_gaps)
        all_gaps = [*structural_gaps, *material_gaps, *contract_gaps, *semantic_gaps]
        comparison = self._comparison(compiled_contract, observed, all_gaps)
        structural_status = "blocked" if structural_gaps else "passed"
        material_status = "blocked" if material_gaps else "passed"
        contract_status = (
            "not_applicable"
            if not compiled_contract.get("contract_id") and not compiled_contract.get("expected_schema")
            else "blocked" if contract_gaps else "passed"
        )
        semantic_status = "blocked" if semantic_gaps or material_gaps or structural_gaps or contract_gaps else "passed"
        profile = ArtifactSemanticProfile(
            artifact_id=artifact_id or None,
            artifact_type=artifact_type or None,
            artifact_path=artifact_path or logical_path,
            artifact_logical_path=str(compiled_contract.get("artifact_logical_path") or logical_path or "") or None,
            artifact_kind=str(compiled_contract.get("artifact_kind") or compiled_contract.get("expected_kind") or "") or None,
            task_run_id=str(compiled_contract.get("task_run_id") or "") or None,
            content_type=content_type,
            declared_contract=compiled_contract,
            expected_kind=compiled_contract.get("expected_kind"),
            expected_schema=list(compiled_contract.get("expected_schema") or []),
            canonical_schema=list(compiled_contract.get("canonical_schema") or compiled_contract.get("expected_schema") or []),
            attribute_contracts=list(compiled_contract.get("attribute_contracts") or []),
            expected_behavior=dict(compiled_contract.get("expected_behavior") or {}),
            expected_semantics=dict(compiled_contract.get("expected_semantics") or {}),
            expected_evidence=list(compiled_contract.get("expected_evidence") or []),
            expected_relationships=list(compiled_contract.get("expected_relationships") or []),
            expected_entities=list(compiled_contract.get("expected_entities") or []),
            expected_cardinality=dict(compiled_contract.get("expected_cardinality") or {}),
            observed_kind=observed.get("kind"),
            observed_schema=list(observed.get("schema") or []),
            observed_behavior=dict(observed.get("behavior") or {}),
            observed_semantics=dict(observed.get("semantics") or {}),
            observed_evidence=list(observed.get("evidence") or []),
            observed_entities=list(compiled_contract.get("observed_entities") or []),
            bound_attribute_observations=bound_observations[:500],
            bound_relationship_observations=bound_relationship_observations[:500],
            relationship_provenance_traces=relationship_provenance_traces[:500],
            relationship_evidence_summary=self._relationship_evidence_summary(compiled_contract, bound_relationship_observations),
            relationship_candidates_by_artifact=self._relationship_candidates_by_artifact(compiled_contract, bound_relationship_observations),
            relationship_confidence_summary=self._relationship_confidence_summary(bound_relationship_observations),
            relationship_conflict_summary=self._relationship_conflict_summary(bound_relationship_observations),
            relationship_negative_evidence_summary=self._relationship_negative_evidence_summary(bound_relationship_observations),
            relationship_binding_quality=self._relationship_binding_quality(bound_relationship_observations, relationship_provenance_traces),
            relationship_rendered_fields=relationship_rendered_fields,
            relationship_rendering_summary=relationship_rendering_summary,
            relationship_validation_results=[
                item.model_dump(mode="json") for item in relationship_validation_results[:500]
            ],
            relationship_validation_summary=relationship_validation_summary,
            validation_ready_count=int(relationship_validation_summary.get("validation_ready_count") or 0),
            validated_relationship_count=int(relationship_validation_summary.get("validated_relationship_count") or 0),
            blocked_relationship_count=int(relationship_validation_summary.get("blocked_relationship_count") or 0),
            conflicted_relationship_count=int(relationship_validation_summary.get("conflicted_relationship_count") or 0),
            truth_eligible_relationship_count=int(relationship_validation_summary.get("truth_eligible_relationship_count") or 0),
            relationship_limitations=self._relationship_limitations(compiled_contract, bound_relationship_observations),
            evidence_summary=self._evidence_summary(compiled_contract, bound_observations, bound_relationship_observations),
            schema_coverage=dict(compiled_contract.get("schema_coverage") or {}),
            perception=dict(compiled_contract.get("perception") or {}),
            semantic_gaps=[*structural_gaps, *material_gaps, *semantic_gaps],
            contract_gaps=contract_gaps,
            comparison=comparison,
            confidence=comparison.confidence,
            completeness_score=self._completeness_score(all_gaps, compiled_contract),
            structural_status=structural_status,
            material_status=material_status,
            semantic_status=semantic_status,
            contract_status=contract_status,
            consistency_status="passed",
        )
        return profile

    def compile_contract(
        self,
        *,
        logical_path: str,
        content_type: str | None = None,
        declared_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        contract = self._contract_for(logical_path)
        compiled: dict[str, Any] = {}
        if contract:
            compiled.update(contract)
            compiled["contract_id"] = str(contract.get("contract_id") or "")
            compiled["required_content_token_groups"] = self._required_groups(contract)
        if declared_contract:
            compiled.update({key: value for key, value in declared_contract.items() if value not in (None, "", [], {})})
        compiled.setdefault("expected_kind", self._expected_kind(logical_path, content_type))
        compiled.setdefault("expected_schema", list(compiled.get("required_schema") or []))
        compiled.setdefault("artifact_logical_path", logical_path)
        compiled.setdefault("artifact_kind", compiled.get("expected_kind"))
        compiled.setdefault("canonical_schema", list(compiled.get("expected_schema") or []))
        return compiled

    def compile_contract_from_prompt(
        self,
        *,
        logical_path: str,
        prompt: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        contract = self.compile_contract(logical_path=logical_path, content_type=content_type)
        fields = self._registered_fields_from_prompt(prompt)
        expected_kind = str(contract.get("expected_kind") or "")
        if fields and expected_kind == "tabular_collection":
            contract["expected_schema"] = fields
            item_label = self._registered_item_label_from_prompt(prompt)
            if item_label:
                contract["expected_entities"] = [{"entity_role": "collection_item", "declared_label": item_label}]
                contract["expected_cardinality"] = {"minimum": 1, "declared_item_label": item_label}
            contract.setdefault("expected_semantics", {})["collection_items_required"] = True
            contract.setdefault("expected_behavior", {})["represents_each_discovered_entity"] = True
        if expected_kind == "evidence_archive":
            contract.setdefault("expected_semantics", {})["contains_evidence_entries"] = True
        return contract

    def compare_profiles(self, profiles: Iterable[ArtifactSemanticProfile]) -> list[ArtifactSemanticProfile]:
        rows = [profile.model_copy(deep=True) for profile in profiles]
        claims_by_key: dict[str, Any] = {}
        for profile in rows:
            claims = profile.observed_semantics.get("claims")
            if not isinstance(claims, dict):
                continue
            for key, value in claims.items():
                if key in claims_by_key and claims_by_key[key] != value:
                    gap = ArtifactSemanticGap(
                        gap_type="artifact_consistency_gap",
                        severity="high",
                        expected={key: claims_by_key[key]},
                        observed={key: value},
                        repair_hint="Reconcile conflicting semantic claims between produced artifacts.",
                        evidence_refs=[profile.artifact_id or profile.artifact_path or ""],
                    )
                    profile.consistency_gaps.append(gap)
                    profile.consistency_status = "blocked"
                    profile.semantic_status = "blocked"
                else:
                    claims_by_key[key] = value
        return rows

    def contract_id_for(self, logical_path: str) -> str | None:
        contract = self._contract_for(logical_path)
        return str(contract.get("contract_id")) if contract else None

    def _validation_from_profile(self, profile: ArtifactSemanticProfile) -> ArtifactSemanticContractValidation:
        gaps = [*profile.semantic_gaps, *profile.contract_gaps, *profile.consistency_gaps]
        missing = [gap.gap_type for gap in gaps if gap.severity in {"medium", "high", "critical"}]
        warnings = [gap.gap_type for gap in gaps if gap.severity in {"info", "low"}]
        status = "passed" if profile.semantic_status == "passed" else "blocked"
        return ArtifactSemanticContractValidation(
            status=status,
            contract_id=str(profile.declared_contract.get("contract_id") or "") or None,
            missing_requirements=list(dict.fromkeys(missing)),
            warnings=list(dict.fromkeys(warnings)),
            profile=profile,
        )

    def _observe(self, content: bytes, *, content_type: str | None, logical_path: str) -> dict[str, Any]:
        expected_kind = self._expected_kind(logical_path, content_type)
        text = content.decode("utf-8", errors="replace")
        observed: dict[str, Any] = {
            "kind": "empty" if not content else "opaque",
            "schema": [],
            "behavior": {},
            "semantics": {},
            "evidence": [],
        }
        if not content:
            return observed
        if expected_kind == "evidence_archive":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = [item.filename for item in archive.infolist() if item.filename]
                observed.update(
                    kind="evidence_archive",
                    schema=["archive_entry"],
                    semantics={"entry_count": len(names), "entries": names},
                    evidence=names[:20],
                )
            except zipfile.BadZipFile:
                observed.update(kind="text_document" if self._looks_like_text(text) else "opaque_binary")
            return observed
        if expected_kind == "tabular_collection":
            try:
                sample = text[:4096]
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
            except Exception:
                dialect = csv.excel
            try:
                reader = csv.DictReader(io.StringIO(text), dialect=dialect)
                schema = [str(item or "").strip() for item in (reader.fieldnames or []) if str(item or "").strip()]
                row_values = list(reader)
                rows = len(row_values)
                identity_map = self._schema_identity_map({"attribute_contracts": []})
                non_empty_by_field: dict[str, int] = {}
                row_samples: list[dict[str, str]] = []
                for row in row_values:
                    sample: dict[str, str] = {}
                    for key, value in row.items():
                        canonical = self._canonical_schema_field(key, identity_map)
                        rendered = "" if value is None else str(value)
                        if rendered.strip():
                            non_empty_by_field[canonical] = non_empty_by_field.get(canonical, 0) + 1
                        if len(sample) < 20:
                            sample[str(key or "")] = rendered[:200]
                    if len(row_samples) < 5:
                        row_samples.append(sample)
                observed.update(
                    kind="tabular_collection",
                    schema=schema,
                    semantics={
                        "row_count": rows,
                        "claims": {"row_count": rows},
                        "non_empty_by_field": non_empty_by_field,
                        "row_samples": row_samples,
                    },
                    evidence=schema,
                )
            except Exception:
                observed.update(kind="text_document" if self._looks_like_text(text) else "opaque")
            return observed
        if expected_kind == "structured_data":
            try:
                parsed = json.loads(text)
                schema = sorted(parsed.keys()) if isinstance(parsed, dict) else ["items"] if isinstance(parsed, list) else ["value"]
                observed.update(
                    kind="structured_data",
                    schema=[str(item) for item in schema],
                    semantics={"json_type": type(parsed).__name__},
                    evidence=[str(item) for item in schema[:20]],
                )
            except Exception:
                observed.update(kind="text_document" if self._looks_like_text(text) else "opaque")
            return observed
        if expected_kind == "document":
            headings = [match.group(1).strip() for match in re.finditer(r"(?m)^#{1,6}\s+(.+)$", text)]
            observed.update(kind="document", schema=headings, semantics={"heading_count": len(headings)}, evidence=headings[:20])
            return observed
        observed.update(kind="text_document" if self._looks_like_text(text) else "opaque_binary")
        return observed

    def _structural_gaps(self, content: bytes) -> list[ArtifactSemanticGap]:
        if content:
            return []
        return [
            ArtifactSemanticGap(
                gap_type="artifact_content_empty",
                severity="high",
                expected="non_empty_artifact_content",
                observed="empty",
                repair_hint="Produce a non-empty artifact before reporting semantic success.",
            )
        ]

    def _material_gaps(self, contract: dict[str, Any], observed: dict[str, Any]) -> list[ArtifactSemanticGap]:
        expected_kind = str(contract.get("expected_kind") or "")
        observed_kind = str(observed.get("kind") or "")
        if not expected_kind or expected_kind == observed_kind:
            return []
        equivalent = {
            ("document", "text_document"),
        }
        if (expected_kind, observed_kind) in equivalent:
            return []
        return [
            ArtifactSemanticGap(
                gap_type="artifact_material_kind_mismatch",
                severity="high",
                expected=expected_kind,
                observed=observed_kind,
                repair_hint="Generate artifact bytes that match the declared artifact kind/content contract.",
                evidence_refs=list(observed.get("evidence") or []),
            )
        ]

    def _contract_gaps(self, contract: dict[str, Any], observed: dict[str, Any], content: bytes) -> list[ArtifactSemanticGap]:
        gaps: list[ArtifactSemanticGap] = []
        identity_map = self._schema_identity_map(contract)
        expected_schema = [
            self._canonical_schema_field(item, identity_map)
            for item in (contract.get("canonical_schema") or contract.get("expected_schema") or [])
            if str(item).strip()
        ]
        observed_schema = {
            self._canonical_schema_field(item, identity_map)
            for item in observed.get("schema") or []
            if str(item).strip()
        }
        for field in expected_schema:
            if field not in observed_schema:
                gaps.append(
                    ArtifactSemanticGap(
                        gap_type=f"artifact_schema_field_missing:{field}",
                        severity="high",
                        expected=field,
                        observed=sorted(observed_schema),
                        repair_hint="Align the artifact schema with the declared artifact contract.",
                    )
                )
        token_groups = contract.get("required_content_token_groups")
        if isinstance(token_groups, dict):
            normalized_content = self._normalize(content.decode("utf-8", errors="replace"))
            for requirement_id, terms in token_groups.items():
                if not self._contains_supported_any(normalized_content, terms):
                    gaps.append(
                        ArtifactSemanticGap(
                            gap_type=str(requirement_id),
                            severity="high",
                            expected=list(terms or []),
                            observed="missing_supported_evidence",
                            repair_hint="Provide supported artifact content for this semantic requirement.",
                        )
                    )
        return gaps

    def _schema_identity_map(self, contract: dict[str, Any]) -> dict[str, str]:
        rows: dict[str, str] = {}
        for item in contract.get("attribute_contracts") or []:
            if not isinstance(item, dict):
                continue
            canonical = self._normalize(str(item.get("canonical_key") or ""))
            if not canonical:
                continue
            candidates = [
                item.get("canonical_key"),
                item.get("display_label"),
                item.get("raw_label"),
                *(item.get("aliases") or [] if isinstance(item.get("aliases"), list) else []),
            ]
            for candidate in candidates:
                normalized = self._normalize(str(candidate or ""))
                if normalized:
                    rows[normalized] = canonical
        return rows

    def _canonical_schema_field(self, value: Any, identity_map: dict[str, str]) -> str:
        normalized = self._normalize(str(value))
        return identity_map.get(normalized, normalized)

    def _semantic_gaps(self, contract: dict[str, Any], observed: dict[str, Any], *, bound_keys: set[str] | None = None) -> list[ArtifactSemanticGap]:
        gaps: list[ArtifactSemanticGap] = []
        bound_keys = bound_keys or set()
        identity_map = self._schema_identity_map(contract)
        expected = contract.get("expected_semantics") if isinstance(contract.get("expected_semantics"), dict) else {}
        observed_semantics = observed.get("semantics") if isinstance(observed.get("semantics"), dict) else {}
        if expected.get("collection_items_required") and int(observed_semantics.get("row_count") or 0) <= 0:
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="artifact_collection_items_missing",
                    severity="high",
                    expected="one_or_more_discovered_entity_rows",
                    observed=observed_semantics.get("row_count", 0),
                    repair_hint="Populate the collection artifact with the discovered entities required by the contract.",
                )
            )
        if expected.get("contains_evidence_entries") and int(observed_semantics.get("entry_count") or 0) <= 0:
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="artifact_evidence_entries_missing",
                    severity="high",
                    expected="one_or_more_evidence_entries",
                    observed=observed_semantics.get("entry_count", 0),
                    repair_hint="Package evidence entries into the governed artifact archive.",
                )
            )
        if expected.get("media_corpus_inventory_required"):
            gaps.extend(self._media_corpus_inventory_gaps(contract, observed))
        for item in contract.get("runtime_semantic_gaps") or []:
            if not isinstance(item, dict):
                continue
            gap_type = str(item.get("gap_type") or "artifact_runtime_semantic_gap")
            if gap_type.startswith("ATTRIBUTE_NOT_OBSERVED:"):
                raw_key = gap_type.split(":", 1)[1]
                canonical = self._canonical_schema_field(raw_key, identity_map)
                if canonical in bound_keys:
                    continue
            gaps.append(
                ArtifactSemanticGap(
                    gap_type=gap_type,
                    reason_code=str(item.get("reason_code") or "") or None,
                    perception_domain=str(item.get("perception_domain") or "") or None,
                    severity=str(item.get("severity") or "medium"),  # type: ignore[arg-type]
                    expected=item.get("expected"),
                    observed=item.get("observed"),
                    confidence=float(item.get("confidence") or 1.0),
                    repair_hint=item.get("repair_hint"),
                    evidence_refs=[str(ref) for ref in item.get("evidence_refs") or [] if ref],
                    details=dict(item.get("details") or {}),
                )
            )
        return gaps

    def _media_corpus_inventory_gaps(self, contract: dict[str, Any], observed: dict[str, Any]) -> list[ArtifactSemanticGap]:
        identity_map = self._schema_identity_map(contract)
        observed_schema = {
            self._canonical_schema_field(item, identity_map)
            for item in observed.get("schema") or []
            if str(item).strip()
        }
        raw_observed_schema = {
            self._normalize(str(item))
            for item in observed.get("schema") or []
            if str(item).strip()
        }
        observed_semantics = observed.get("semantics") if isinstance(observed.get("semantics"), dict) else {}
        non_empty = observed_semantics.get("non_empty_by_field") if isinstance(observed_semantics.get("non_empty_by_field"), dict) else {}
        gaps: list[ArtifactSemanticGap] = []
        findings_shape = {self._normalize(item) for item in ("severity", "title", "summary")}
        identity_fields = {self._normalize("entity_id")}
        source_root_role = self._normalize("source_root_role")
        evidence_ref = self._normalize("evidence_ref")
        limitations = self._normalize("limitations")
        metadata_status = self._normalize("metadata_status")
        if findings_shape.issubset(raw_observed_schema) and not observed_schema.intersection({*identity_fields, source_root_role}):
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="media_inventory_findings_shape_mismatch",
                    reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                    severity="critical",
                    expected="media_corpus_inventory_rows",
                    observed=sorted(observed_schema),
                    repair_hint="Materialize diagnostic findings under a findings contract, not under a media/corpus inventory contract.",
                )
            )
        if int(observed_semantics.get("row_count") or 0) <= 0:
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="media_inventory_rows_missing",
                    reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                    severity="high",
                    expected="one_or_more_media_or_corpus_entity_rows",
                    observed=0,
                    repair_hint="Populate the inventory with observed corpus/media entities or block the artifact explicitly.",
                )
            )
        if not observed_schema.intersection(identity_fields):
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="media_inventory_entity_identity_missing",
                    reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                    severity="high",
                    expected=sorted(identity_fields),
                    observed=sorted(observed_schema),
                    repair_hint="Include stable entity identity fields before validating a media/corpus inventory.",
                )
            )
        if source_root_role not in observed_schema:
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="media_inventory_source_root_role_missing",
                    reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                    severity="high",
                    expected="source_root_role",
                    observed=sorted(observed_schema),
                    repair_hint="Preserve corpus/project root role in inventory rows so phase dependencies can audit workspace separation.",
                )
            )
        if contract.get("expected_semantics", {}).get("evidence_ref_required"):
            evidence_count = int(non_empty.get(evidence_ref) or 0)
            if evidence_ref not in observed_schema or evidence_count <= 0:
                gaps.append(
                    ArtifactSemanticGap(
                        gap_type="media_inventory_evidence_ref_missing",
                        reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                        severity="high",
                        expected="non_empty_evidence_ref",
                        observed={"schema": sorted(observed_schema), "non_empty_evidence_ref_rows": evidence_count},
                        repair_hint="Bind each inventory row to evidence refs before semantic validation can pass.",
                    )
                )
        if contract.get("expected_semantics", {}).get("explicit_limitations_required"):
            limitation_count = int(non_empty.get(limitations) or 0)
            if limitations not in observed_schema or limitation_count <= 0:
                gaps.append(
                    ArtifactSemanticGap(
                        gap_type="media_inventory_limitations_missing",
                        reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
                        severity="medium",
                        expected="explicit_limitations_or_none",
                        observed={"schema": sorted(observed_schema), "non_empty_limitations_rows": limitation_count},
                        repair_hint="State inventory limitations explicitly, including absent metadata capability or partial observations.",
                    )
                )
        if metadata_status in observed_schema:
            metadata_values = self._sample_values_for_field(observed_semantics, metadata_status)
            unavailable_values = {
                self._normalize(item)
                for item in ("not_configured", "not_observed", "missing_dependency", "unknown", "blocked", "unsupported", "")
            }
            normalized_values = {self._normalize(value) for value in metadata_values}
            if (normalized_values and normalized_values.issubset(unavailable_values)) or not metadata_values:
                gaps.append(
                    ArtifactSemanticGap(
                        gap_type="media_inventory_metadata_capability_unavailable",
                        reason_code="MUSIC_INVENTORY_PARTIAL_EVIDENCE",
                        perception_domain="observational_cognition",
                        severity="medium",
                        expected="metadata_observed_or_explicit_partial_contract",
                        observed=sorted(normalized_values) if normalized_values else "metadata_status_declared_without_observed_rows",
                        repair_hint="Represent the inventory as partial or blocked when media metadata remains unavailable.",
                    )
                )
        return gaps

    def _sample_values_for_field(self, observed_semantics: dict[str, Any], canonical_field: str) -> list[str]:
        row_samples = observed_semantics.get("row_samples")
        if not isinstance(row_samples, list):
            return []
        values: list[str] = []
        for row in row_samples:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if self._normalize(str(key or "")) == canonical_field:
                    values.append(str(value or ""))
        return values

    def _bound_attribute_observations(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        binding = contract.get("artifact_observation_binding") if isinstance(contract.get("artifact_observation_binding"), dict) else {}
        summary_rows = binding.get("bound_observations") if isinstance(binding.get("bound_observations"), list) else []
        if summary_rows:
            return [dict(item) for item in summary_rows if isinstance(item, dict)]
        bound_counts = binding.get("bound_counts_by_canonical_key") if isinstance(binding.get("bound_counts_by_canonical_key"), dict) else {}
        if bound_counts:
            rows: list[dict[str, Any]] = []
            for key, count in bound_counts.items():
                canonical = str(key or "")
                if not canonical:
                    continue
                rows.append(
                    {
                        "observation_id": f"bound_summary:{canonical}",
                        "entity_id": None,
                        "canonical_key": canonical,
                        "attribute_name": canonical,
                        "evidence_refs": [],
                        "capability_id": None,
                        "observer_id": None,
                        "confidence": 1.0,
                        "provenance": {
                            "source": "artifact_observation_binding",
                            "record_count": int(count or 0),
                        },
                    }
                )
            return rows
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        rows = perception.get("attribute_observations") if isinstance(perception.get("attribute_observations"), list) else []
        bound: list[dict[str, Any]] = []
        identity_map = self._schema_identity_map(contract)
        for item in rows:
            if not isinstance(item, dict):
                continue
            if item.get("observation_state") != "observed":
                continue
            value = item.get("observed_value")
            if value in (None, ""):
                continue
            canonical = self._canonical_schema_field(item.get("canonical_key") or item.get("attribute_name") or "", identity_map)
            if not canonical:
                continue
            bound.append(
                {
                    "observation_id": item.get("observation_id"),
                    "entity_id": item.get("entity_id"),
                    "canonical_key": canonical,
                    "attribute_name": item.get("attribute_name") or canonical,
                    "evidence_refs": list(item.get("evidence_refs") or []),
                    "capability_id": item.get("capability_id"),
                    "observer_id": item.get("observer_id"),
                    "confidence": float(item.get("confidence") or 0.0),
                    "provenance": dict(item.get("provenance") or {}),
                }
            )
        return bound

    def _bound_relationship_observations(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        binding = contract.get("artifact_relationship_binding") if isinstance(contract.get("artifact_relationship_binding"), dict) else {}
        summary_rows = binding.get("bound_relationship_observations") if isinstance(binding.get("bound_relationship_observations"), list) else []
        if summary_rows:
            return [dict(item) for item in summary_rows if isinstance(item, dict)]
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        rows = perception.get("relationship_observations") if isinstance(perception.get("relationship_observations"), list) else []
        candidates = perception.get("relationship_candidates") if isinstance(perception.get("relationship_candidates"), list) else []
        candidate_by_id = {
            str(item.get("candidate_id")): item
            for item in candidates
            if isinstance(item, dict) and item.get("candidate_id")
        }
        bound: list[dict[str, Any]] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "")
            candidate = candidate_by_id.get(candidate_id, {})
            bound.append(
                {
                    "observation_id": item.get("observation_id"),
                    "candidate_id": candidate_id,
                    "source_entity_id": candidate.get("source_entity_id"),
                    "target_entity_id": candidate.get("target_entity_id"),
                    "relation_family": item.get("observed_relation_family") or candidate.get("relation_family"),
                    "relation_kind_candidate": item.get("observed_relation_kind_candidate") or candidate.get("relation_kind_candidate"),
                    "evidence_refs": list(item.get("evidence_refs") or candidate.get("evidence_refs") or []),
                    "capability_id": item.get("producer_capability_id") or candidate.get("producer_capability_id"),
                    "confidence": float(item.get("confidence") or candidate.get("confidence") or 0.0),
                    "confidence_model": dict(item.get("confidence_model") or candidate.get("confidence_model") or {}),
                    "provenance_trace_id": item.get("provenance_trace_id") or candidate.get("provenance_trace_id"),
                    "truth_eligible": False,
                    "validation_required": True,
                    "provenance": dict(candidate.get("provenance") or {}),
                    "negative_evidence": list(item.get("negative_evidence") or candidate.get("negative_evidence") or []),
                    "conflicts": list(item.get("conflicts") or candidate.get("conflicts") or []),
                    "limitations": list(candidate.get("limitations") or []),
                }
            )
        return bound

    def _relationship_provenance_traces(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        binding = contract.get("artifact_relationship_binding") if isinstance(contract.get("artifact_relationship_binding"), dict) else {}
        rows = binding.get("relationship_provenance_traces") if isinstance(binding.get("relationship_provenance_traces"), list) else []
        if rows:
            return [dict(item) for item in rows if isinstance(item, dict)]
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        traces = perception.get("relationship_provenance_traces") if isinstance(perception.get("relationship_provenance_traces"), list) else []
        return [dict(item) for item in traces if isinstance(item, dict)]

    def _relationship_evidence_records(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        binding = contract.get("artifact_relationship_binding") if isinstance(contract.get("artifact_relationship_binding"), dict) else {}
        rows = binding.get("relationship_evidence_records") if isinstance(binding.get("relationship_evidence_records"), list) else []
        if rows:
            return [dict(item) for item in rows if isinstance(item, dict)]
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        evidence_set = perception.get("evidence_set") if isinstance(perception.get("evidence_set"), dict) else {}
        records = evidence_set.get("records") if isinstance(evidence_set.get("records"), list) else []
        return [
            dict(item)
            for item in records
            if isinstance(item, dict) and item.get("evidence_type") == "relationship_observation"
        ]

    def _bound_observed_keys(self, contract: dict[str, Any], observations: list[dict[str, Any]]) -> set[str]:
        identity_map = self._schema_identity_map(contract)
        return {
            self._canonical_schema_field(item.get("canonical_key") or item.get("attribute_name") or "", identity_map)
            for item in observations
            if item.get("canonical_key") or item.get("attribute_name")
        }

    def _bound_evidence_refs(self, observations: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for item in observations:
            refs.extend(str(ref) for ref in item.get("evidence_refs") or [] if ref)
        return list(dict.fromkeys(refs))

    def _count_by_key(self, rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in rows:
            value = str(item.get(key) or "")
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts

    def _evidence_summary(
        self,
        contract: dict[str, Any],
        observations: list[dict[str, Any]],
        relationship_observations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        evidence_set = perception.get("evidence_set") if isinstance(perception.get("evidence_set"), dict) else {}
        records = evidence_set.get("records") if isinstance(evidence_set.get("records"), list) else []
        media = perception.get("media_metadata_capability") if isinstance(perception.get("media_metadata_capability"), dict) else {}
        return {
            "bound_attribute_observation_count": len(observations),
            "bound_relationship_observation_count": len(relationship_observations or []),
            "bound_observed_attributes": sorted({str(item.get("canonical_key")) for item in observations if item.get("canonical_key")}),
            "evidence_record_count": len(records),
            "media_metadata_capability": {
                "status": media.get("status"),
                "selected_backend": media.get("selected_backend"),
                "evidence_records_created": media.get("evidence_records_created"),
                "attributes_observed": list(media.get("attributes_observed") or []),
                "attributes_missing": list(media.get("attributes_missing") or []),
            }
            if media
            else {},
        }

    def _relationship_gaps(
        self,
        contract: dict[str, Any],
        relationship_observations: list[dict[str, Any]],
        validation_summary: dict[str, Any] | None = None,
    ) -> list[ArtifactSemanticGap]:
        expected = contract.get("expected_relationships") if isinstance(contract.get("expected_relationships"), list) else []
        relationship_semantics = contract.get("relationship_semantics") if isinstance(contract.get("relationship_semantics"), dict) else {}
        required = bool(expected or relationship_semantics.get("relationship_candidates_required"))
        if not required:
            return []
        if not relationship_observations:
            return [
                ArtifactSemanticGap(
                    gap_type="relationship_candidate_missing",
                    reason_code="RELATIONSHIP_EVIDENCE_INSUFFICIENT",
                    perception_domain="relationship_cognition",
                    severity="medium",
                    expected="relationship_candidate_present",
                    observed="missing",
                    repair_hint="Produce relationship candidates through the governed capability path before validating relationship semantics.",
                )
            ]
        gaps: list[ArtifactSemanticGap] = []
        if not any(item.get("provenance_trace_id") for item in relationship_observations):
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="relationship_provenance_missing",
                    reason_code="RELATIONSHIP_PROVENANCE_MISSING",
                    perception_domain="relationship_cognition",
                    severity="medium",
                    expected="relationship_provenance_trace",
                    observed="missing",
                    repair_hint="Bind relationship provenance traces before future readiness assessment.",
                )
            )
        if any(item.get("conflicts") for item in relationship_observations):
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="relationship_conflict_present",
                    reason_code="RELATIONSHIP_CONFLICT_BLOCKED",
                    perception_domain="relationship_cognition",
                    severity="medium",
                    expected="no_blocking_relationship_conflicts",
                    observed="conflict_present",
                    repair_hint="Resolve or preserve relationship conflict state before readiness assessment.",
                )
            )
        summary = validation_summary or {}
        if int(summary.get("blocked_relationship_count") or 0) > 0:
            reason_codes = summary.get("reason_codes") if isinstance(summary.get("reason_codes"), list) else []
            gaps.append(
                ArtifactSemanticGap(
                    gap_type="relationship_validation_blocked",
                    reason_code="RELATIONSHIP_AMBIGUITY_UNRESOLVED"
                    if "RELATIONSHIP_AMBIGUITY_UNRESOLVED" in reason_codes
                    else "RELATIONSHIP_VALIDATION_REQUIRED",
                    perception_domain="relationship_cognition",
                    severity="medium",
                    expected="relationship_validation_ready_or_validated",
                    observed="relationship_validation_blocked",
                    repair_hint="Resolve relationship validation blockers before any final relation claim.",
                )
            )
        gaps.append(
            ArtifactSemanticGap(
                gap_type="relationship_final_validation_missing",
                reason_code="RELATIONSHIP_VALIDATION_REQUIRED",
                perception_domain="relationship_cognition",
                severity="medium",
                expected="validated_relationship",
                observed="relationship_candidate_present",
                repair_hint="Run a later relationship validation layer before promoting candidates to final relationship claims.",
                evidence_refs=[
                    str(ref)
                    for item in relationship_observations[:20]
                    for ref in item.get("evidence_refs", [])
                    if ref
                ],
                details={
                    "relationship_candidate_present": True,
                    "relationship_not_truth_eligible": True,
                },
            )
        )
        return gaps

    def _relationship_evidence_summary(self, contract: dict[str, Any], relationship_observations: list[dict[str, Any]]) -> dict[str, Any]:
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        evidence = perception.get("relationship_evidence") if isinstance(perception.get("relationship_evidence"), list) else []
        reason_codes: list[str] = []
        if relationship_observations:
            if not any(item.get("provenance_trace_id") for item in relationship_observations):
                reason_codes.append("RELATIONSHIP_PROVENANCE_MISSING")
            if any(item.get("conflicts") for item in relationship_observations):
                reason_codes.append("RELATIONSHIP_CONFLICT_PRESENT")
            reason_codes.append("RELATIONSHIP_VALIDATION_REQUIRED")
        else:
            reason_codes.append("RELATIONSHIP_EVIDENCE_INSUFFICIENT")
        return {
            "relationship_candidate_present": bool(relationship_observations),
            "relationship_evidence_present": bool(evidence or relationship_observations),
            "relationship_provenance_present": any(item.get("provenance_trace_id") for item in relationship_observations),
            "relationship_final_validation_missing": bool(relationship_observations),
            "relationship_not_truth_eligible": True,
            "candidate_count": len(relationship_observations),
            "evidence_signal_count": len(evidence),
            "reason_codes": list(dict.fromkeys(reason_codes)),
        }

    def _relationship_candidates_by_artifact(self, contract: dict[str, Any], relationship_observations: list[dict[str, Any]]) -> dict[str, int]:
        path = str(contract.get("artifact_logical_path") or contract.get("artifact_id") or "unbound")
        return {path: len(relationship_observations)} if relationship_observations else {}

    def _relationship_confidence_summary(self, relationship_observations: list[dict[str, Any]]) -> dict[str, Any]:
        values = [float(item.get("confidence") or 0.0) for item in relationship_observations]
        bands: dict[str, int] = {}
        for item in relationship_observations:
            model = item.get("confidence_model") if isinstance(item.get("confidence_model"), dict) else {}
            band = str(model.get("confidence_band") or "")
            if band:
                bands[band] = bands.get(band, 0) + 1
        if not values:
            return {"count": 0, "max": 0.0, "average": 0.0, "bands": bands}
        return {"count": len(values), "max": round(max(values), 4), "average": round(sum(values) / len(values), 4), "bands": bands}

    def _relationship_conflict_summary(self, relationship_observations: list[dict[str, Any]]) -> dict[str, Any]:
        conflicts = [
            item
            for observation in relationship_observations
            for item in observation.get("conflicts", [])
            if isinstance(item, dict)
        ]
        by_code: dict[str, int] = {}
        blocking = 0
        for item in conflicts:
            code = str(item.get("code") or "unknown_conflict")
            by_code[code] = by_code.get(code, 0) + 1
            if item.get("blocks_validation_ready", True):
                blocking += 1
        return {"conflict_count": len(conflicts), "blocking_conflict_count": blocking, "by_code": by_code}

    def _relationship_negative_evidence_summary(self, relationship_observations: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [
            item
            for observation in relationship_observations
            for item in observation.get("negative_evidence", [])
            if isinstance(item, dict)
        ]
        by_code: dict[str, int] = {}
        total_penalty = 0.0
        for item in rows:
            code = str(item.get("code") or "unknown_negative_evidence")
            by_code[code] = by_code.get(code, 0) + 1
            total_penalty += float(item.get("confidence_penalty") or 0.0)
        return {"negative_evidence_count": len(rows), "total_confidence_penalty": round(total_penalty, 4), "by_code": by_code}

    def _relationship_binding_quality(self, relationship_observations: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, Any]:
        trace_ids = {str(item.get("trace_id") or "") for item in traces if item.get("trace_id")}
        observations_with_trace = [
            item
            for item in relationship_observations
            if item.get("provenance_trace_id") and str(item.get("provenance_trace_id")) in trace_ids
        ]
        missing_trace = max(0, len(relationship_observations) - len(observations_with_trace))
        return {
            "status": "complete" if relationship_observations and missing_trace == 0 else "partial" if relationship_observations else "empty",
            "observation_count": len(relationship_observations),
            "provenance_trace_count": len(traces),
            "observations_with_trace": len(observations_with_trace),
            "observations_missing_trace": missing_trace,
            "truth_eligible": False,
        }

    def _relationship_rendered_fields(
        self,
        contract: dict[str, Any],
        relationship_observations: list[dict[str, Any]],
        traces: list[dict[str, Any]],
        validation_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields = [
            str(item)
            for item in contract.get("relationship_fields", [])
            if str(item).strip()
        ] or [
            "relationship_candidate_summary",
            "relationship_candidate_count",
            "relationship_top_family",
            "relationship_confidence_band",
            "relationship_validation_status",
            "relationship_evidence_ref_count",
            "relationship_provenance_ref_count",
            "relationship_conflict_count",
            "relationship_validation_reason_codes",
            "relationship_validation_ready_count",
            "relationship_conflicted_count",
            "relationship_limitations_summary",
        ]
        validation_summary = validation_summary or {}
        families = [
            str(item.get("relation_family") or "")
            for item in relationship_observations
            if item.get("relation_family")
        ]
        family_counts: dict[str, int] = {}
        for family in families:
            family_counts[family] = family_counts.get(family, 0) + 1
        top_family = sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))[0][0] if family_counts else None
        confidence_bands = [
            str((item.get("confidence_model") or {}).get("confidence_band") or "")
            for item in relationship_observations
            if isinstance(item.get("confidence_model"), dict)
        ]
        confidence_band = confidence_bands[0] if confidence_bands else None
        evidence_ref_count = len({
            str(ref)
            for item in relationship_observations
            for ref in item.get("evidence_refs", []) or []
            if ref
        })
        provenance_ref_count = len({
            str(item.get("provenance_trace_id"))
            for item in relationship_observations
            if item.get("provenance_trace_id")
        } | {str(item.get("trace_id")) for item in traces if item.get("trace_id")})
        conflict_count = sum(len(item.get("conflicts") or []) for item in relationship_observations)
        limitation_count = sum(len(item.get("limitations") or []) for item in relationship_observations)
        validation_ready_count = int(validation_summary.get("validation_ready_count") or 0)
        conflicted_count = int(validation_summary.get("conflicted_relationship_count") or 0)
        validation_status = (
            "validated"
            if int(validation_summary.get("validated_relationship_count") or 0) > 0
            else "validation_ready"
            if validation_ready_count > 0
            else "conflicted"
            if conflicted_count > 0
            else "validation_required"
            if relationship_observations
            else "blocked"
        )
        values = {
            "relationship_candidate_summary": {
                "candidate_count": len(relationship_observations),
                "top_family": top_family,
                "confidence_band": confidence_band,
                "validation_status": validation_status,
                "truth_eligible": False,
            },
            "relationship_candidate_count": len(relationship_observations),
            "relationship_candidate_families": sorted(family_counts),
            "relationship_top_family": top_family,
            "relationship_confidence_band": confidence_band,
            "relationship_validation_status": validation_status,
            "relationship_validation_reason_codes": list(validation_summary.get("reason_codes") or []),
            "relationship_validation_ready_count": validation_ready_count,
            "relationship_conflicted_count": conflicted_count,
            "relationship_evidence_ref_count": evidence_ref_count,
            "relationship_provenance_ref_count": provenance_ref_count,
            "relationship_conflict_count": conflict_count,
            "relationship_limitations_summary": {
                "limitation_count": limitation_count,
                "candidate_only": True,
                "truth_eligible": False,
            },
        }
        return {field: values.get(field) for field in fields if field in values}

    def _relationship_rendering_summary(
        self,
        fields: dict[str, Any],
        relationship_observations: list[dict[str, Any]],
        traces: list[dict[str, Any]],
        validation_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        validation_summary = validation_summary or {}
        validation_status = str(fields.get("relationship_validation_status") or ("validation_required" if relationship_observations else "blocked"))
        return {
            "status": "available" if relationship_observations and fields else "blocked" if relationship_observations else "not_available",
            "rendered_field_count": len(fields),
            "candidate_count": len(relationship_observations),
            "evidence_ref_count": int(fields.get("relationship_evidence_ref_count") or 0),
            "provenance_ref_count": int(fields.get("relationship_provenance_ref_count") or len(traces)),
            "truth_eligible": False,
            "validation_status": validation_status,
            "validation_ready_count": int(validation_summary.get("validation_ready_count") or 0),
            "validated_relationship_count": int(validation_summary.get("validated_relationship_count") or 0),
            "conflicted_relationship_count": int(validation_summary.get("conflicted_relationship_count") or 0),
            "validation_reason_codes": list(validation_summary.get("reason_codes") or []),
            "source": "ArtifactSemanticProfile.relationship_binding",
        }

    def _relationship_limitations(self, contract: dict[str, Any], relationship_observations: list[dict[str, Any]]) -> list[str]:
        limitations = [
            str(item)
            for observation in relationship_observations
            for item in observation.get("limitations", [])
            if item
        ]
        if relationship_observations:
            limitations.extend(["relationship_candidates_are_not_final_truth", "relationship_validation_required"])
        return list(dict.fromkeys(limitations))

    def _comparison(self, contract: dict[str, Any], observed: dict[str, Any], gaps: list[ArtifactSemanticGap]) -> SemanticComparison:
        expected_parts = []
        if contract.get("expected_kind"):
            expected_parts.append("kind")
        if contract.get("expected_schema"):
            expected_parts.append("schema")
        if contract.get("required_content_token_groups"):
            expected_parts.append("content_contract")
        if contract.get("expected_semantics"):
            expected_parts.append("semantics")
        missing_parts = [gap.gap_type for gap in gaps]
        matches = [part for part in expected_parts if not any(part in gap for gap in missing_parts)]
        distance = 0.0 if not expected_parts else min(1.0, len(missing_parts) / max(1, len(expected_parts)))
        return SemanticComparison(matches=matches, missing_parts=missing_parts, semantic_distance=distance, confidence=1.0)

    def _completeness_score(self, gaps: list[ArtifactSemanticGap], contract: dict[str, Any]) -> float:
        expected_weight = 1
        expected_weight += 1 if contract.get("expected_kind") else 0
        expected_weight += len(contract.get("expected_schema") or [])
        expected_weight += len(contract.get("required_content_token_groups") or {})
        expected_weight += len(contract.get("expected_semantics") or {})
        penalty = sum(1 for gap in gaps if gap.severity in {"medium", "high", "critical"})
        return max(0.0, min(1.0, (expected_weight - penalty) / max(1, expected_weight)))

    def _expected_kind(self, logical_path: str, content_type: str | None) -> str:
        value = f"{logical_path} {content_type or ''}".casefold()
        suffix = Path(str(logical_path or "")).suffix.casefold()
        if "application/zip" in value or suffix == ".zip":
            return "evidence_archive"
        if "text/csv" in value or suffix == ".csv":
            return "tabular_collection"
        if "application/json" in value or suffix == ".json":
            return "structured_data"
        if "markdown" in value or suffix == ".md":
            return "document"
        if "text/" in value or suffix in {".txt", ".log"}:
            return "document"
        return "opaque"

    def _registered_fields_from_prompt(self, prompt: str) -> list[str]:
        normalized_prompt = str(prompt or "").replace("\r\n", "\n")
        patterns = [
            r"(?is)(?:para\s+cada|for\s+each)\s+.+?\s+(?:registrar|record)\s*:\s*(?P<body>.+?)(?:\n\s*\n|Artifacts?|Artefatos?|Success|Contrato|$)",
            r"(?is)(?:campos|fields)\s*:\s*(?P<body>.+?)(?:\n\s*\n|Artifacts?|Artefatos?|Success|Contrato|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized_prompt)
            if not match:
                continue
            fields = []
            for raw_line in match.group("body").splitlines():
                line = raw_line.strip().strip("-*•:;,.")
                if not line:
                    continue
                if len(line) > 80:
                    continue
                fields.append(self._field_id(line))
            if fields:
                return list(dict.fromkeys(fields))
        return []

    def _registered_item_label_from_prompt(self, prompt: str) -> str | None:
        normalized_prompt = str(prompt or "").replace("\r\n", "\n")
        patterns = [
            r"(?is)(?:para\s+cada|for\s+each)\s+(?P<label>.+?)\s+(?:registrar|record)\s*:",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized_prompt)
            if not match:
                continue
            label = self._field_id(match.group("label"))
            return label or None
        return None

    def _field_id(self, value: str) -> str:
        normalized = self._normalize(value)
        return normalized.replace(" ", "_")

    def _artifact_path(self, artifact: dict[str, Any]) -> Path | None:
        raw = artifact.get("local_path") or artifact.get("storage_path") or artifact.get("storage_ref")
        if not raw:
            return None
        path = Path(str(raw))
        if not path.is_absolute():
            path = PATHS.project_root / path
        return path

    def _looks_like_text(self, value: str) -> bool:
        if not value:
            return False
        return "\ufffd" not in value[:2000]

    def _legacy_token_validation(self, logical_path: str, content: str) -> ArtifactSemanticContractValidation:
        contract = self._contract_for(logical_path)
        if not contract:
            return ArtifactSemanticContractValidation(status="not_applicable")
        normalized_content = self._normalize(content)
        missing = [
            requirement_id
            for requirement_id, terms in self._required_groups(contract).items()
            if not self._contains_supported_any(normalized_content, terms)
        ]
        return ArtifactSemanticContractValidation(
            status="blocked" if missing else "passed",
            contract_id=str(contract.get("contract_id") or ""),
            missing_requirements=missing,
        )

    def _contract_for(self, logical_path: str) -> dict[str, Any] | None:
        normalized_path = self._normalize(logical_path)
        for contract in self.policy.get("contracts", []) or []:
            if not isinstance(contract, dict):
                continue
            groups = contract.get("path_token_groups") or []
            if all(self._contains_any(normalized_path, group) for group in groups):
                return contract
        return None

    def _required_groups(self, contract: dict[str, Any]) -> dict[str, list[str]]:
        value = contract.get("required_content_token_groups")
        if not isinstance(value, dict):
            return {}
        return {str(key): [str(item) for item in terms or []] for key, terms in value.items()}

    def _contains_any(self, text: str, terms: Any) -> bool:
        if isinstance(terms, str):
            terms = [terms]
        if not isinstance(terms, list):
            return False
        return any(self._token_present(text, str(term)) for term in terms if str(term).strip())

    def _contains_supported_any(self, text: str, terms: Any) -> bool:
        if isinstance(terms, str):
            terms = [terms]
        if not isinstance(terms, list):
            return False
        return any(self._supported_token_present(text, str(term)) for term in terms if str(term).strip())

    def _token_present(self, text: str, term: str) -> bool:
        normalized = self._normalize(term)
        if not normalized:
            return False
        if re.search(r"\w", normalized):
            return bool(re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text))
        return normalized in text

    def _supported_token_present(self, text: str, term: str) -> bool:
        normalized = self._normalize(term)
        if not normalized:
            return False
        pattern = rf"(?<!\w){re.escape(normalized)}(?!\w)" if re.search(r"\w", normalized) else re.escape(normalized)
        for match in re.finditer(pattern, text):
            window = self._evidence_window(text, match.start(), match.end())
            if not self._has_unsupported_evidence_marker(window):
                return True
        return False

    def _evidence_window(self, text: str, start: int, end: int) -> str:
        section_start = text.rfind("##", 0, start)
        section_end = text.find("##", end)
        if section_start >= 0:
            return text[section_start: section_end if section_end >= 0 else min(len(text), end + 300)]
        return text[max(0, start - 60): min(len(text), end + 120)]

    def _has_unsupported_evidence_marker(self, text: str) -> bool:
        terms = self.policy.get("unsupported_evidence_terms") or []
        return self._contains_any(text, terms)

    def _normalize(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.casefold().replace("_", " ").replace("-", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()
