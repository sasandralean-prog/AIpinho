from __future__ import annotations

from aipinho.schemas.intent.workspace_resolution import TargetReference, WorkspaceResolution
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService


class WorkspaceResolver:
    def __init__(
        self,
        concept_matcher: ConceptMatcher | None = None,
        workspace_policy: WorkspacePolicyService | None = None,
        path_extractor: PathExtractionService | None = None,
    ) -> None:
        self.concept_matcher = concept_matcher or ConceptMatcher().load()
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.path_extractor = path_extractor or PathExtractionService()

    def resolve(self, prompt: str, matches: list[ConceptMatch], *, self_reference: bool) -> WorkspaceResolution:
        extracted = self.path_extractor.extract_first(prompt)
        if extracted:
            path = extracted.value
            policy = self.workspace_policy.evaluate(workspace_path=path, requires_workspace=True)
            return WorkspaceResolution(
                path=path,
                declared=True,
                protected=policy.blocked,
                requires_clarification=False,
                reason=policy.reason,
            )
        if self_reference:
            return WorkspaceResolution(path=None, declared=False, protected=False, requires_clarification=False, reason="self_reference_no_workspace_required")
        normalized = self.concept_matcher.normalize(prompt)
        vague_project = "nesse projeto" in normalized or "neste projeto" in normalized or "esse projeto" in normalized
        if vague_project:
            return WorkspaceResolution(path=None, declared=False, protected=False, requires_clarification=True, reason="vague_project_reference")
        return WorkspaceResolution(path=None, declared=False, protected=False, requires_clarification=False, reason="no_workspace_reference")

    def target_for(self, workspace: WorkspaceResolution, *, self_reference: bool) -> TargetReference:
        if self_reference:
            return TargetReference(kind="self", value=None, confidence=0.9)
        if workspace.path:
            return TargetReference(kind="workspace", value=workspace.path, confidence=1.0)
        return TargetReference(kind="none", value=None, confidence=0.0)
