from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.semantic_graph_revision import (
    SemanticGraphRevision,
    SemanticGraphRevisionProposal,
)


class SemanticGraphRevisionAuthorityService:
    """Computes deterministic intent and canonical revision authority hashes."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def intent_payload(
        self,
        proposal: SemanticGraphRevisionProposal,
    ) -> dict[str, Any]:
        return {
            "parent_graph_id": proposal.parent_graph_id,
            "parent_graph_authority_sha256": (
                proposal.parent_graph_authority_sha256
            ),
            "parent_revision_id": proposal.parent_revision_id,
            "revision_number": proposal.revision_number,
            "reason": proposal.reason,
            "provenance": dict(proposal.provenance),
            "add_work_units": [
                item.model_dump(mode="json")
                for item in proposal.add_work_units
            ],
            "add_edges": [
                item.model_dump(mode="json")
                for item in proposal.add_edges
            ],
            "remove_edge_ids": list(proposal.remove_edge_ids),
            "remove_work_unit_ids": list(
                proposal.remove_work_unit_ids
            ),
            "schema_version": proposal.schema_version,
        }

    def compute_intent_sha256(
        self,
        proposal: SemanticGraphRevisionProposal,
    ) -> str:
        return self.stable_sha256(self.intent_payload(proposal))

    def revision_payload(
        self,
        revision: SemanticGraphRevision,
    ) -> dict[str, Any]:
        return {
            "revision_number": revision.revision_number,
            "parent_revision_id": revision.parent_revision_id,
            "parent_graph_id": revision.parent_graph_id,
            "parent_graph_authority_sha256": (
                revision.parent_graph_authority_sha256
            ),
            "child_graph_id": revision.child_graph_id,
            "child_graph_authority_sha256": (
                revision.child_graph_authority_sha256
            ),
            "revision_intent_sha256": revision.revision_intent_sha256,
            "reason": revision.reason,
            "provenance": dict(revision.provenance),
            "added_work_unit_ids": list(
                revision.added_work_unit_ids
            ),
            "added_edge_ids": list(revision.added_edge_ids),
            "removed_work_unit_ids": list(
                revision.removed_work_unit_ids
            ),
            "removed_edge_ids": list(revision.removed_edge_ids),
            "edges_requiring_demand_recompile": list(
                revision.edges_requiring_demand_recompile
            ),
            "schema_version": revision.schema_version,
        }

    def compute_revision_sha256(
        self,
        revision: SemanticGraphRevision,
    ) -> str:
        return self.stable_sha256(self.revision_payload(revision))

    def verify(self, revision: SemanticGraphRevision) -> bool:
        return (
            revision.authority_sha256
            == self.compute_revision_sha256(revision)
        )
