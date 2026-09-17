from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.remote_repository_scope import RemoteRepositoryScopeDecision
from aipinho.services.policy_kernel.remote_repository_identity_service import RemoteRepositoryIdentityService
from aipinho.utils.yaml_loader import load_yaml_file


class RemoteRepositoryScopeService:
    """Canonical repository + branch + operation scope gate.

    This service never executes Git or network operations. It only evaluates the
    frozen mission scope and global network safety facets for later executors.
    """

    PROMOTION_OPERATIONS = {"git_push"}
    DESTRUCTIVE_OPERATIONS = {
        "git_force_push",
        "git_remote_delete",
        "git_branch_delete",
        "git_history_rewrite",
    }

    def __init__(
        self,
        identities: RemoteRepositoryIdentityService | None = None,
        policy_path: Path | None = None,
    ) -> None:
        self.identities = identities or RemoteRepositoryIdentityService()
        path = policy_path or PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        policy = load_yaml_file(path, critical=True, root=path.parent)
        network = policy.get("network", {}) if isinstance(policy.get("network"), dict) else {}
        self.denied_hosts = {str(item).casefold() for item in network.get("denied_hosts", []) or []}
        self.denied_schemes = {str(item).casefold() for item in network.get("denied_schemes", []) or []}

    def decide(
        self,
        *,
        remote_resources: list[MissionResourceScope],
        repository_locator: str,
        branch: str | None,
        operation: str,
        observed_repository_locator: str | None = None,
    ) -> RemoteRepositoryScopeDecision:
        try:
            requested = self.identities.normalize(repository_locator)
        except ValueError:
            return self._deny("remote_repository_identity_invalid", operation=operation, branch=branch)
        global_reason = self._global_denial_reason(requested)
        if global_reason:
            return self._deny(
                global_reason,
                identity=requested.normalized_identity,
                provider=requested.provider,
                operation=operation,
                branch=branch,
            )
        matches = [
            item
            for item in remote_resources
            if item.resource_type == "remote_repository"
            and item.normalized_identity == requested.normalized_identity
        ]
        denied = next(
            (
                item
                for item in matches
                if item.role == "remote_denied"
                or any(c.effect == "deny" and c.kind == "repository_access" for c in item.constraints)
            ),
            None,
        )
        if denied is not None:
            return self._deny(
                "remote_repository_explicitly_denied",
                identity=requested.normalized_identity,
                provider=requested.provider,
                resource=denied,
                operation=operation,
                branch=branch,
            )
        allowed = next((item for item in matches if item.role != "remote_denied"), None)
        if allowed is None:
            return self._deny(
                "remote_repository_not_declared",
                identity=requested.normalized_identity,
                provider=requested.provider,
                operation=operation,
                branch=branch,
            )
        if bool(allowed.metadata.get("secret_material_detected")):
            return self._deny(
                "remote_repository_secret_material_detected",
                identity=requested.normalized_identity,
                provider=requested.provider,
                resource=allowed,
                operation=operation,
                branch=branch,
            )
        if operation in self.DESTRUCTIVE_OPERATIONS:
            return self._deny(
                "remote_destructive_operation_denied",
                identity=requested.normalized_identity,
                provider=requested.provider,
                resource=allowed,
                operation=operation,
                branch=branch,
            )
        if operation not in set(allowed.permissions):
            return self._deny(
                "remote_operation_not_declared",
                identity=requested.normalized_identity,
                provider=requested.provider,
                resource=allowed,
                operation=operation,
                branch=branch,
            )
        if not allowed.allowed_branches:
            return self._clarify(
                "remote_branch_scope_missing",
                requested.normalized_identity,
                allowed,
                operation,
                branch=branch,
            )
        if not branch:
            return self._clarify(
                "remote_branch_required", requested.normalized_identity, allowed, operation
            )
        if branch not in set(allowed.allowed_branches):
            return self._deny(
                "remote_branch_not_allowed",
                identity=requested.normalized_identity,
                provider=requested.provider,
                resource=allowed,
                operation=operation,
                branch=branch,
            )
        if operation in self.PROMOTION_OPERATIONS:
            if not observed_repository_locator:
                return self._clarify(
                    "remote_identity_reobservation_required",
                    requested.normalized_identity,
                    allowed,
                    operation,
                    branch=branch,
                )
            try:
                observed = self.identities.normalize(observed_repository_locator)
            except ValueError:
                return self._deny(
                    "observed_remote_repository_identity_invalid",
                    identity=requested.normalized_identity,
                    provider=requested.provider,
                    resource=allowed,
                    operation=operation,
                    branch=branch,
                )
            if observed.normalized_identity != requested.normalized_identity:
                return self._deny(
                    "remote_identity_changed_before_promotion",
                    identity=requested.normalized_identity,
                    provider=requested.provider,
                    resource=allowed,
                    operation=operation,
                    branch=branch,
                )
        return RemoteRepositoryScopeDecision(
            status="allowed",
            reason_code="remote_scope_allows_operation",
            repository_identity=requested.normalized_identity,
            resource_id=allowed.resource_id,
            branch=branch,
            operation=operation,
            provider=requested.provider,
            evidence_refs=[*allowed.provenance_refs, f"remote_resource:{allowed.resource_id}"],
        )
    def _global_denial_reason(self, identity) -> str | None:
        if identity.secret_material_detected:
            return "remote_repository_secret_material_detected"
        if identity.host.casefold() in self.denied_hosts:
            return "remote_repository_host_denied"
        if identity.scheme.casefold() in self.denied_schemes:
            return "remote_repository_scheme_denied"
        return None

    def _deny(
        self,
        reason: str,
        *,
        identity: str | None = None,
        provider: str | None = None,
        resource: MissionResourceScope | None = None,
        operation: str | None = None,
        branch: str | None = None,
    ) -> RemoteRepositoryScopeDecision:
        return RemoteRepositoryScopeDecision(
            status="denied",
            reason_code=reason,
            repository_identity=identity,
            resource_id=resource.resource_id if resource else None,
            branch=branch,
            operation=operation,
            provider=provider,
            evidence_refs=list(resource.provenance_refs) if resource else [],
        )
    def _clarify(
        self,
        reason: str,
        identity: str,
        resource: MissionResourceScope,
        operation: str,
        *,
        branch: str | None = None,
    ) -> RemoteRepositoryScopeDecision:
        return RemoteRepositoryScopeDecision(
            status="needs_clarification",
            reason_code=reason,
            repository_identity=identity,
            resource_id=resource.resource_id,
            branch=branch,
            operation=operation,
            provider=resource.provider,
            evidence_refs=list(resource.provenance_refs),
        )
