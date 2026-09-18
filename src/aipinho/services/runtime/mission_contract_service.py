from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionAuthorityEvidence,
    MissionCompletionContract,
    MissionConstraint,
    MissionContract,
    MissionExecutionMode,
    MissionResourceScope,
)
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.policy_kernel.mission_staging_policy_service import MissionStagingPolicyService


_EXECUTION_MODES = {
    "single_operation",
    "staged",
    "end_to_end_governed",
}


class MissionContractService:
    """Freezes mission intent before planning and enforces monotonic authority.

    This service consumes already-structured intent. It may hash source prompt text
    for provenance, but it never reparses free-form prompt text to infer new
    capabilities, resources, authority, or continuation semantics.
    """

    def __init__(
        self,
        *,
        staging_policy: MissionStagingPolicyService | None = None,
    ) -> None:
        self.staging_policy = staging_policy or MissionStagingPolicyService()

    def resolve_for_request(
        self,
        request: TaskRunRequest,
        *,
        inherited: MissionContract | None = None,
    ) -> MissionContract:
        supplied = request.mission_contract
        if supplied is not None:
            if not self.verify(supplied):
                raise ValueError("mission_contract_authority_hash_invalid")
            if inherited is not None:
                self.validate_child_contract(parent=inherited, child=supplied)
            return supplied
        if inherited is not None:
            return inherited
        return self.compile_from_request(request)

    def compile_from_request(self, request: TaskRunRequest) -> MissionContract:
        intent = dict(request.intent_map or {})
        prompt_sha = self._source_prompt_sha256(request=request, intent=intent)
        source_message_id = self._source_message_id(
            request=request,
            intent=intent,
            prompt_sha=prompt_sha,
        )
        objective = self._first_text(
            intent,
            "objective",
            "semantic_goal",
            "goal",
            "intent_type",
        ) or str(request.operation_type or request.contract_type)
        strategy = self._strategy(intent)
        mission_id = self._mission_id(
            request=request,
            intent=intent,
            source_message_id=source_message_id,
            prompt_sha=prompt_sha,
            objective=objective,
        )

        requested = self._ordered_unique(
            [
                *request.capabilities_required,
                *self._string_list(intent.get("requested_capabilities")),
                *self._string_list(intent.get("capabilities_required")),
            ]
        )
        authorized = self._ordered_unique(
            self._string_list(intent.get("authorized_capabilities"))
        )
        authority_evidence = self._authority_evidence(
            intent.get("authority_evidence"),
            prompt_sha=prompt_sha,
            authorized_capabilities=authorized,
        )
        local_resources = self._resource_list(
            intent.get("local_resources"),
            expected_types={"local_workspace"},
        )
        remote_resources = self._resource_list(
            intent.get("remote_resources"),
            expected_types={"remote_repository", "external_resource"},
        )
        negative_constraints = self._constraints(
            intent.get("negative_constraints"),
            prefix="mission_constraint",
        )
        completion = MissionCompletionContract(
            validation_requirements=self._ordered_unique(
                self._string_list(intent.get("validation_requirements"))
            ),
            completion_requirements=self._ordered_unique(
                self._string_list(intent.get("completion_requirements"))
            ),
            allow_limited_completion=bool(intent.get("allow_limited_completion", False)),
        )
        provenance = self._ordered_unique(
            [
                f"source_message:{source_message_id}",
                *self._string_list(intent.get("mission_provenance_refs")),
            ]
        )

        contract = MissionContract(
            mission_id=mission_id,
            session_id=request.session_id,
            source_message_id=source_message_id,
            source_prompt_sha256=prompt_sha,
            objective=objective,
            semantic_context=self._semantic_context(intent),
            strategy=strategy,
            local_resources=local_resources,
            remote_resources=remote_resources,
            authority=MissionAuthorityBinding(
                requested_capabilities=requested,
                authorized_capabilities=authorized,
                source_refs=self._ordered_unique(
                    self._string_list(intent.get("authority_source_refs"))
                ),
                explicit_evidence=authority_evidence,
            ),
            negative_constraints=negative_constraints,
            completion=completion,
            provenance_refs=provenance,
            revision=1,
            authority_sha256="pending",
        )
        return self.freeze(contract)

    def freeze(self, contract: MissionContract) -> MissionContract:
        authority = self.authority_sha256(contract)
        return contract.model_copy(update={"authority_sha256": authority})

    def verify(self, contract: MissionContract) -> bool:
        return bool(contract.authority_sha256) and (
            contract.authority_sha256 == self.authority_sha256(contract)
        )

    def authority_sha256(self, contract: MissionContract) -> str:
        payload = contract.model_dump(mode="json")
        payload.pop("authority_sha256", None)
        payload.pop("frozen_at", None)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def validate_child_contract(
        self,
        *,
        parent: MissionContract,
        child: MissionContract,
    ) -> None:
        if not self.verify(parent) or not self.verify(child):
            raise ValueError("mission_contract_authority_hash_invalid")
        immutable_pairs = {
            "mission_id": (parent.mission_id, child.mission_id),
            "session_id": (parent.session_id, child.session_id),
            "source_message_id": (parent.source_message_id, child.source_message_id),
            "source_prompt_sha256": (
                parent.source_prompt_sha256,
                child.source_prompt_sha256,
            ),
            "objective": (parent.objective, child.objective),
            "semantic_context": (
                parent.semantic_context,
                child.semantic_context,
            ),
            "strategy": (parent.strategy, child.strategy),
        }
        if any(before != after for before, after in immutable_pairs.values()):
            raise ValueError("mission_contract_child_identity_mismatch")
        if child.authority_sha256 == parent.authority_sha256:
            if child.revision != parent.revision:
                raise ValueError("mission_contract_child_revision_mismatch")
            return
        if child.revision != parent.revision + 1:
            raise ValueError("mission_contract_child_revision_mismatch")
        if child.parent_authority_sha256 != parent.authority_sha256:
            raise ValueError("mission_contract_child_parent_authority_mismatch")

        if not set(child.authority.requested_capabilities).issubset(
            set(parent.authority.requested_capabilities)
        ):
            raise ValueError("mission_contract_child_expands_requested_capabilities")
        if not set(child.authority.authorized_capabilities).issubset(
            set(parent.authority.authorized_capabilities)
        ):
            raise ValueError("mission_contract_child_expands_authority")
        self._validate_resource_narrowing(
            parent.local_resources,
            child.local_resources,
            scope="local",
            parent_contract=parent,
        )
        self._validate_resource_narrowing(
            parent.remote_resources,
            child.remote_resources,
            scope="remote",
        )
        parent_constraints = {
            self._stable_json(item.model_dump(mode="json"))
            for item in parent.negative_constraints
        }
        child_constraints = {
            self._stable_json(item.model_dump(mode="json"))
            for item in child.negative_constraints
        }
        if not parent_constraints.issubset(child_constraints):
            raise ValueError("mission_contract_child_weakens_negative_constraints")
        if not set(parent.completion.validation_requirements).issubset(
            set(child.completion.validation_requirements)
        ):
            raise ValueError("mission_contract_child_weakens_validation_requirements")
        if not set(parent.completion.completion_requirements).issubset(
            set(child.completion.completion_requirements)
        ):
            raise ValueError("mission_contract_child_weakens_completion_requirements")
        if (
            not parent.completion.allow_limited_completion
            and child.completion.allow_limited_completion
        ):
            raise ValueError("mission_contract_child_weakens_completion_policy")

    def narrowed_child(
        self,
        parent: MissionContract,
        *,
        requested_capabilities: list[str] | None = None,
        authorized_capabilities: list[str] | None = None,
        local_resources: list[MissionResourceScope] | None = None,
        remote_resources: list[MissionResourceScope] | None = None,
        additional_constraints: list[MissionConstraint] | None = None,
        additional_validation_requirements: list[str] | None = None,
        additional_completion_requirements: list[str] | None = None,
        allow_limited_completion: bool | None = None,
    ) -> MissionContract:
        child = parent.model_copy(
            update={
                "authority": MissionAuthorityBinding(
                    requested_capabilities=self._ordered_unique(
                        requested_capabilities
                        if requested_capabilities is not None
                        else parent.authority.requested_capabilities
                    ),
                    authorized_capabilities=self._ordered_unique(
                        authorized_capabilities
                        if authorized_capabilities is not None
                        else parent.authority.authorized_capabilities
                    ),
                    source_refs=list(parent.authority.source_refs),
                    explicit_evidence=list(parent.authority.explicit_evidence),
                ),
                "local_resources": list(
                    local_resources if local_resources is not None else parent.local_resources
                ),
                "remote_resources": list(
                    remote_resources if remote_resources is not None else parent.remote_resources
                ),
                "negative_constraints": [
                    *parent.negative_constraints,
                    *(additional_constraints or []),
                ],
                "completion": MissionCompletionContract(
                    validation_requirements=self._ordered_unique(
                        [
                            *parent.completion.validation_requirements,
                            *(additional_validation_requirements or []),
                        ]
                    ),
                    completion_requirements=self._ordered_unique(
                        [
                            *parent.completion.completion_requirements,
                            *(additional_completion_requirements or []),
                        ]
                    ),
                    allow_limited_completion=(
                        parent.completion.allow_limited_completion
                        if allow_limited_completion is None
                        else bool(allow_limited_completion)
                    ),
                ),
                "revision": parent.revision + 1,
                "parent_authority_sha256": parent.authority_sha256,
                "authority_sha256": "pending",
            }
        )
        child = self.freeze(child)
        self.validate_child_contract(parent=parent, child=child)
        return child

    def _validate_resource_narrowing(
        self,
        parent_resources: list[MissionResourceScope],
        child_resources: list[MissionResourceScope],
        *,
        scope: str,
        parent_contract: MissionContract | None = None,
    ) -> None:
        parent_by_id = {item.resource_id: item for item in parent_resources}
        for child in child_resources:
            parent = parent_by_id.get(child.resource_id)
            if parent is None:
                if (
                    scope == "local"
                    and child.resource_type == "mission_staging"
                    and parent_contract is not None
                ):
                    self.staging_policy.validate_derived_resource(
                        parent=parent_contract,
                        resource=child,
                    )
                    continue
                raise ValueError(f"mission_contract_child_adds_{scope}_resource")

            immutable = (
                parent.resource_type == child.resource_type
                and parent.role == child.role
                and parent.locator == child.locator
                and parent.provider == child.provider
                and parent.normalized_identity == child.normalized_identity
                and parent.derived_from == child.derived_from
                and parent.metadata == child.metadata
            )
            if not immutable:
                raise ValueError("mission_contract_child_changes_resource_identity")
            if not set(child.permissions).issubset(set(parent.permissions)):
                raise ValueError("mission_contract_child_expands_resource_permissions")
            if not set(child.allowed_branches).issubset(set(parent.allowed_branches)):
                raise ValueError("mission_contract_child_expands_resource_branches")
            parent_constraints = {
                self._stable_json(item.model_dump(mode="json"))
                for item in parent.constraints
            }
            child_constraints = {
                self._stable_json(item.model_dump(mode="json"))
                for item in child.constraints
            }
            if not parent_constraints.issubset(child_constraints):
                raise ValueError("mission_contract_child_weakens_resource_constraints")

    def _source_prompt_sha256(
        self,
        *,
        request: TaskRunRequest,
        intent: dict[str, Any],
    ) -> str:
        supplied = self._first_text(intent, "source_prompt_sha256", "prompt_sha256")
        if supplied:
            return supplied
        for key in ("raw_prompt", "source_prompt"):
            value = intent.get(key)
            if value is None:
                continue
            prompt = str(value)
            if prompt:
                return self._sha256(prompt)
        structured = {
            "session_id": request.session_id,
            "source_channel": request.source_channel,
            "operation_type": request.operation_type,
            "contract_type": request.contract_type,
            "intent_map": self._without_raw_prompt(intent),
        }
        return self._sha256(self._stable_json(structured))

    def _source_message_id(
        self,
        *,
        request: TaskRunRequest,
        intent: dict[str, Any],
        prompt_sha: str,
    ) -> str:
        supplied = request.source_message_id or self._first_text(
            intent,
            "source_message_id",
            "message_id",
        )
        if supplied:
            return supplied
        seed = self._stable_json(
            {
                "session_id": request.session_id,
                "source_channel": request.source_channel,
                "source_prompt_sha256": prompt_sha,
            }
        )
        return f"message_ref_{self._sha256(seed)[:24]}"

    def _mission_id(
        self,
        *,
        request: TaskRunRequest,
        intent: dict[str, Any],
        source_message_id: str,
        prompt_sha: str,
        objective: str,
    ) -> str:
        supplied = self._first_text(intent, "mission_id")
        if supplied:
            return supplied
        seed = self._stable_json(
            {
                "session_id": request.session_id,
                "source_message_id": source_message_id,
                "source_prompt_sha256": prompt_sha,
                "objective": objective,
            }
        )
        return f"mission_{self._sha256(seed)[:24]}"

    def _semantic_context(self, intent: dict[str, Any]) -> dict[str, Any]:
        semantic_graph = intent.get("semantic_intent_graph")
        if hasattr(semantic_graph, "model_dump"):
            semantic_graph = semantic_graph.model_dump(mode="json")
        semantic_graph = (
            dict(semantic_graph) if isinstance(semantic_graph, dict) else {}
        )
        context: dict[str, Any] = {
            "intent_type": self._first_text(intent, "intent_type"),
            "operation_type": self._first_text(intent, "operation_type"),
            "semantic_intent_graph": semantic_graph,
            "future_side_effect_intent": bool(
                intent.get("future_side_effect_intent", False)
            ),
        }
        strategy = intent.get("mission_execution_strategy")
        if isinstance(strategy, dict):
            context["mission_execution_strategy"] = {
                "mode": str(strategy.get("mode") or "")
            }
        for key in (
            "requested_deliverables",
            "validation_requirements",
            "completion_requirements",
        ):
            values = self._string_list(intent.get(key))
            if values:
                context[key] = values
        return {
            key: value
            for key, value in context.items()
            if value not in (None, "", [], {})
        }

    def _strategy(self, intent: dict[str, Any]) -> MissionExecutionMode:
        value = intent.get("mission_execution_strategy")
        if isinstance(value, dict):
            value = value.get("mode")
        if value is None:
            value = intent.get("mission_mode") or intent.get("mission_strategy")
        mode = str(value or "single_operation").strip()
        return mode if mode in _EXECUTION_MODES else "single_operation"

    def _resource_list(
        self,
        value: Any,
        *,
        expected_types: set[str],
    ) -> list[MissionResourceScope]:
        if not isinstance(value, list):
            return []
        resources: list[MissionResourceScope] = []
        for item in value:
            if isinstance(item, MissionResourceScope):
                resource = item
            elif isinstance(item, dict):
                resource = MissionResourceScope.model_validate(item)
            else:
                continue
            if resource.resource_type not in expected_types:
                raise ValueError("mission_contract_resource_type_mismatch")
            resource = resource.model_copy(
                update={
                    "permissions": self._ordered_unique(resource.permissions),
                    "allowed_branches": self._ordered_unique(resource.allowed_branches),
                    "constraints": sorted(
                        resource.constraints,
                        key=lambda constraint: constraint.constraint_id,
                    ),
                    "provenance_refs": self._ordered_unique(resource.provenance_refs),
                }
            )
            resources.append(resource)
        return sorted(resources, key=lambda item: item.resource_id)

    def _authority_evidence(
        self,
        value: Any,
        *,
        prompt_sha: str,
        authorized_capabilities: list[str],
    ) -> list[MissionAuthorityEvidence]:
        if not authorized_capabilities:
            return []
        if not isinstance(value, list) or not value:
            raise ValueError("mission_contract_authority_evidence_missing")
        evidence = [MissionAuthorityEvidence.model_validate(item) for item in value if isinstance(item, dict)]
        if not evidence:
            raise ValueError("mission_contract_authority_evidence_missing")
        if any(item.source_prompt_sha256 != prompt_sha for item in evidence):
            raise ValueError("mission_contract_authority_prompt_hash_mismatch")
        covered = {capability for item in evidence for capability in item.capabilities}
        if not set(authorized_capabilities).issubset(covered):
            raise ValueError("mission_contract_authority_evidence_incomplete")
        return evidence

    def _constraints(
        self,
        value: Any,
        *,
        prefix: str,
    ) -> list[MissionConstraint]:
        if not isinstance(value, list):
            return []
        constraints: list[MissionConstraint] = []
        for index, item in enumerate(value):
            if isinstance(item, MissionConstraint):
                constraints.append(item)
            elif isinstance(item, dict):
                constraints.append(MissionConstraint.model_validate(item))
            elif str(item).strip():
                text = str(item).strip()
                constraints.append(
                    MissionConstraint(
                        constraint_id=f"{prefix}_{self._sha256(text)[:16]}",
                        kind="semantic_constraint",
                        effect="deny",
                        value=text,
                        source_ref=f"structured_constraint:{index}",
                    )
                )
        return sorted(constraints, key=lambda item: item.constraint_id)

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, (list, tuple, set)):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _ordered_unique(self, values: Iterable[str]) -> list[str]:
        return sorted({str(value).strip() for value in values if str(value).strip()})

    def _first_text(self, values: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = values.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _without_raw_prompt(self, intent: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in intent.items()
            if key not in {"raw_prompt", "source_prompt"}
        }

    def _stable_json(self, value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def _sha256(self, value: str) -> str:
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
