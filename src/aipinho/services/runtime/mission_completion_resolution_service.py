from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionBindingProposal,
    MissionCompletionResolution,
)
from aipinho.services.runtime.mission_completion_binding_compiler import (
    MissionCompletionBindingCompiler,
)
from aipinho.services.runtime.mission_completion_binding_proposal_service import (
    MissionCompletionBindingProposalService,
)
from aipinho.services.runtime.mission_completion_evidence_catalog_service import (
    MissionCompletionEvidenceCatalogService,
)
from aipinho.services.runtime.mission_completion_facet_service import (
    MissionCompletionFacetService,
)
from aipinho.services.runtime.mission_completion_projection_service import (
    MissionCompletionProjectionService,
)
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository
from aipinho.services.runtime.task_run_store import TaskRunStore


class MissionCompletionResolutionService:
    """Resolve mission completion from persisted interpretation + canonical evidence.

    Semantic proposals are non-authoritative and persisted only after deterministic
    structural compilation succeeds. Rehydration recompiles the exact persisted
    proposal against current canonical evidence without silently re-invoking a model.
    """

    PERSISTED_PROPOSAL_KEY = "mission_completion_binding_proposal"

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        projection: MissionCompletionProjectionService | None = None,
        catalog: MissionCompletionEvidenceCatalogService | None = None,
        proposer: MissionCompletionBindingProposalService | None = None,
        compiler: MissionCompletionBindingCompiler | None = None,
        facets: MissionCompletionFacetService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        outcomes = PhaseOutcomeRepository(store=self.store)
        self.projection = projection or MissionCompletionProjectionService(
            store=self.store,
            outcomes=outcomes,
        )
        self.catalog = catalog or MissionCompletionEvidenceCatalogService(
            outcomes=outcomes,
        )
        self.proposer = proposer or MissionCompletionBindingProposalService()
        self.compiler = compiler or MissionCompletionBindingCompiler()
        self.facets = facets or MissionCompletionFacetService()

    def resolve(
        self,
        *,
        mission_id: str,
        anchor_run_id: str | None = None,
        allow_inference: bool = True,
    ) -> MissionCompletionResolution:
        snapshot = self.projection.project(mission_id=mission_id)
        if snapshot.status == "missing":
            return self._resolution(
                mission_id=mission_id,
                status="unavailable",
                reason_codes=list(snapshot.reason_codes),
                snapshot_sha=snapshot.authority_sha256,
            )
        if snapshot.status == "invalid":
            facet = self.facets.evaluate(snapshot, evaluations=[])
            return self._resolution(
                mission_id=mission_id,
                status=facet.status,
                reason_codes=list(facet.reason_codes),
                snapshot_sha=snapshot.authority_sha256,
                facet=facet,
            )

        catalog = self.catalog.build(snapshot)
        proposal = self._find_persisted_proposal(
            mission_id=mission_id,
            snapshot_sha=snapshot.authority_sha256,
            catalog_sha=catalog.authority_sha256,
        )
        proposal_source = "persisted" if proposal is not None else "none"

        if proposal is None:
            if not allow_inference:
                return self._resolution(
                    mission_id=mission_id,
                    status="unavailable",
                    reason_codes=[
                        "MISSION_COMPLETION_BINDING_PROPOSAL_NOT_PERSISTED"
                    ],
                    snapshot_sha=snapshot.authority_sha256,
                    catalog_sha=catalog.authority_sha256,
                )
            proposal = self.proposer.propose(snapshot, catalog)
            proposal_source = "generated"
            if proposal.status != "candidate":
                return self._resolution(
                    mission_id=mission_id,
                    status="unavailable",
                    reason_codes=[proposal.reason_code],
                    snapshot_sha=snapshot.authority_sha256,
                    catalog_sha=catalog.authority_sha256,
                    proposal_sha=proposal.proposal_sha256,
                    proposal_source=proposal_source,
                )

        compilation = self.compiler.compile(
            snapshot,
            catalog,
            proposal,
        )
        if compilation.status != "compiled":
            return self._resolution(
                mission_id=mission_id,
                status="blocked",
                reason_codes=list(compilation.reason_codes),
                snapshot_sha=snapshot.authority_sha256,
                catalog_sha=catalog.authority_sha256,
                proposal_sha=proposal.proposal_sha256,
                proposal_source=proposal_source,
                compilation_status=compilation.status,
            )

        if proposal_source == "generated":
            persisted = self._persist_proposal(
                proposal,
                mission_id=mission_id,
                anchor_run_id=anchor_run_id,
            )
            if not persisted:
                return self._resolution(
                    mission_id=mission_id,
                    status="blocked",
                    reason_codes=[
                        "MISSION_COMPLETION_BINDING_PROPOSAL_PERSIST_FAILED"
                    ],
                    snapshot_sha=snapshot.authority_sha256,
                    catalog_sha=catalog.authority_sha256,
                    proposal_sha=proposal.proposal_sha256,
                    proposal_source=proposal_source,
                    compilation_status=compilation.status,
                )

        facet = self.facets.evaluate(
            snapshot,
            evaluations=compilation.evaluations,
        )
        return self._resolution(
            mission_id=mission_id,
            status=facet.status,
            reason_codes=list(facet.reason_codes),
            snapshot_sha=snapshot.authority_sha256,
            catalog_sha=catalog.authority_sha256,
            proposal_sha=proposal.proposal_sha256,
            proposal_source=proposal_source,
            compilation_status=compilation.status,
            facet=facet,
        )

    def _find_persisted_proposal(
        self,
        *,
        mission_id: str,
        snapshot_sha: str,
        catalog_sha: str,
    ) -> MissionCompletionBindingProposal | None:
        runs = sorted(
            self.store.list_runs(mission_id=mission_id, limit=1000),
            key=lambda item: (
                str(item.created_at or ""),
                str(item.run_id),
            ),
            reverse=True,
        )
        for run in runs:
            payload = (
                run.intent_map.get(self.PERSISTED_PROPOSAL_KEY)
                if isinstance(run.intent_map, dict)
                else None
            )
            if not isinstance(payload, dict):
                continue
            try:
                proposal = MissionCompletionBindingProposal.model_validate(
                    payload
                )
            except Exception:
                continue
            if (
                proposal.mission_id == mission_id
                and proposal.snapshot_authority_sha256 == snapshot_sha
                and proposal.catalog_authority_sha256 == catalog_sha
                and proposal.status == "candidate"
            ):
                return proposal
        return None

    def _persist_proposal(
        self,
        proposal: MissionCompletionBindingProposal,
        *,
        mission_id: str,
        anchor_run_id: str | None,
    ) -> bool:
        run = (
            self.store.get_run(anchor_run_id)
            if anchor_run_id
            else None
        )
        if (
            run is None
            or run.mission_binding is None
            or run.mission_binding.mission_id != mission_id
        ):
            runs = sorted(
                self.store.list_runs(mission_id=mission_id, limit=1000),
                key=lambda item: (
                    str(item.created_at or ""),
                    str(item.run_id),
                ),
                reverse=True,
            )
            run = runs[0] if runs else None
        if run is None:
            return False

        run.intent_map[self.PERSISTED_PROPOSAL_KEY] = proposal.model_dump(
            mode="json"
        )
        self.store.update_run(run)
        return True

    def _resolution(
        self,
        *,
        mission_id: str,
        status: str,
        reason_codes: list[str],
        snapshot_sha: str | None = None,
        catalog_sha: str | None = None,
        proposal_sha: str | None = None,
        proposal_source: str = "none",
        compilation_status: str | None = None,
        facet=None,
    ) -> MissionCompletionResolution:
        return MissionCompletionResolution(
            mission_id=mission_id,
            status=status,
            reason_codes=list(dict.fromkeys(reason_codes)),
            snapshot_authority_sha256=snapshot_sha,
            catalog_authority_sha256=catalog_sha,
            proposal_sha256=proposal_sha,
            proposal_source=proposal_source,
            compilation_status=compilation_status,
            facet=facet,
        )
