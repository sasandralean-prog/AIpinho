from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from aipinho.schemas.runtime.mission_contract import MissionConstraint, MissionResourceScope
from aipinho.services.governance.intent.intent_normalizer import normalize_text
from aipinho.services.policy_kernel.remote_repository_identity_service import RemoteRepositoryIdentityService


@dataclass(frozen=True)
class IntentRemoteRepositoryResolution:
    resources: list[MissionResourceScope]
    mission_constraints: list[MissionConstraint]


class IntentRemoteRepositoryService:
    """Compiles prompt-declared repository scope at semantic ingress only."""

    _LOCATOR_RE = re.compile(
        r"(?:https?|ssh|git)://[^\s<>\"']+|git@[A-Za-z0-9.-]+:[^\s<>\"']+|"
        r"(?:github\.com|gitlab\.com|bitbucket\.org)/[A-Za-z0-9_.\-/]+",
        re.IGNORECASE,
    )
    _BRANCH_RE = re.compile(
        r"\b(?:branch|ramo)\s*[:=]?\s*[`\"']?([A-Za-z0-9._/-]+)",
        re.IGNORECASE,
    )
    _NEGATIVE_PREFIXES = (
        "nao use",
        "nao utilize",
        "nao acesse",
        "nao faca push para",
        "do not use",
        "don't use",
        "do not access",
        "forbid",
        "proib",
    )

    def __init__(self, identities: RemoteRepositoryIdentityService | None = None) -> None:
        self.identities = identities or RemoteRepositoryIdentityService()

    def resolve(self, prompt: str) -> IntentRemoteRepositoryResolution:
        text = str(prompt or "")
        references: list[tuple[re.Match[str], object, bool]] = []
        for match in self._LOCATOR_RE.finditer(text):
            locator = self._trim_locator(match.group(0))
            try:
                identity = self.identities.normalize(locator)
            except ValueError:
                continue
            references.append((match, identity, self._is_negative_reference(text, match.start())))

        positive_indexes = [index for index, (_match, _identity, denied) in enumerate(references) if not denied]
        branch_mentions = self._branch_mentions(text)
        permission_mentions = self._permission_mentions(text)
        resources: list[MissionResourceScope] = []
        seen: set[tuple[str, bool]] = set()

        for index, (match, identity, denied) in enumerate(references):
            key = (identity.normalized_identity, denied)
            if key in seen:
                continue
            seen.add(key)
            branches = [] if denied else self._assigned_values(text, index, references, positive_indexes, branch_mentions)
            permissions = [] if denied else self._assigned_values(text, index, references, positive_indexes, permission_mentions)
            constraints = [
                MissionConstraint(
                    constraint_id=f"remote_destructive_{self._digest(identity.normalized_identity)}",
                    kind="git_destructive",
                    effect="deny",
                    subject=identity.normalized_identity,
                    value=["force_push", "remote_delete", "branch_delete", "history_rewrite"],
                    source_ref="prompt_remote_scope",
                )
            ]
            if denied:
                constraints.append(
                    MissionConstraint(
                        constraint_id=f"remote_deny_{self._digest(identity.normalized_identity)}",
                        kind="repository_access",
                        effect="deny",
                        subject=identity.normalized_identity,
                        value="all",
                        source_ref="prompt_negative_remote_scope",
                    )
                )
            resources.append(
                MissionResourceScope(
                    resource_id=f"remote_{self._digest(identity.normalized_identity)}_{'deny' if denied else 'allow'}",
                    resource_type="remote_repository",
                    role="remote_denied" if denied else "remote_allowed",
                    locator=identity.normalized_locator,
                    provider=identity.provider,
                    normalized_identity=identity.normalized_identity,
                    allowed_branches=branches,
                    permissions=permissions,
                    constraints=constraints,
                    provenance_refs=["prompt_remote_repository_scope", "normalized_remote_identity"],
                    metadata={
                        "host": identity.host,
                        "scheme_observed": identity.scheme,
                        "secret_material_detected": identity.secret_material_detected,
                    },
                )
            )
        mission_constraints = self._mission_constraints(text)
        return IntentRemoteRepositoryResolution(
            resources=sorted(resources, key=lambda item: item.resource_id),
            mission_constraints=sorted(mission_constraints, key=lambda item: item.constraint_id),
        )

    def _branch_mentions(self, text: str) -> list[tuple[int, str]]:
        mentions: list[tuple[int, str]] = []
        for match in self._BRANCH_RE.finditer(text):
            branch = match.group(1).strip().strip(".,;:()[]{}")
            if branch:
                mentions.append((match.start(), branch))
        return mentions

    def _permission_mentions(self, text: str) -> list[tuple[int, str]]:
        normalized = normalize_text(text)
        patterns = (
            (
                "git_clone",
                r"\bgit\s+clone\b|\bclonar\b|\bclone\s+o\s+repositorio\b|"
                r"\b(?:obtenha|use|crie)\s+(?:uma\s+)?copia\s+git\s+limpa\b|"
                r"\bcopia\s+git\s+limpa\b",
            ),
            ("git_fetch", r"\bgit\s+fetch\b|\bfetch\b|\bbuscar\s+refs\b|\batualizar\s+refs\b"),
            (
                "git_pull_ff",
                r"\bgit\s+pull\b|\bpull\s+fast-forward\b|\bpull\s+--ff-only\b|"
                r"\bfast[- ]forward\s+seguro\b|\bff-only\b",
            ),
            ("git_commit", r"\bgit\s+commit\b|\bfaca\s+commit\b|\bcrie\s+commit\b"),
            ("git_push", r"\bgit\s+push\b|\bfaca\s+push\b|\benvie\s+para\s+o\s+remoto\b"),
        )
        mentions: list[tuple[int, str]] = []
        for permission, pattern in patterns:
            mentions.extend((match.start(), permission) for match in re.finditer(pattern, normalized))
        return sorted(mentions)

    def _assigned_values(
        self,
        text: str,
        reference_index: int,
        references: list[tuple[re.Match[str], object, bool]],
        positive_indexes: list[int],
        mentions: list[tuple[int, str]],
    ) -> list[str]:
        if reference_index not in positive_indexes:
            return []
        reference_spans = [(match.start(), match.end()) for match, _identity, _denied in references]
        separators = [
            match.start()
            for match in re.finditer(r"[.!?;\n]", text)
            if not any(start <= match.start() < end for start, end in reference_spans)
        ]
        assigned: set[str] = set()
        for position, value in mentions:
            left_candidates = [item for item in separators if item < position]
            right_candidates = [item for item in separators if item > position]
            left = (max(left_candidates) + 1) if left_candidates else 0
            right = min(right_candidates) if right_candidates else len(text)
            candidates = [
                index
                for index in positive_indexes
                if left <= references[index][0].start() < right
            ]
            if len(candidates) == 1:
                target = candidates[0]
            elif len(candidates) > 1:
                target = min(
                    candidates,
                    key=lambda candidate: abs(position - references[candidate][0].start()),
                )
            elif len(positive_indexes) == 1:
                target = positive_indexes[0]
            else:
                continue
            if target == reference_index:
                assigned.add(value)
        return sorted(assigned)

    def _is_negative_reference(self, text: str, start: int) -> bool:
        prefix = text[max(0, start - 96):start]
        normalized = normalize_text(prefix)
        sentence = re.split(r"[.!?;\n]", normalized)[-1]
        return any(marker in sentence for marker in self._NEGATIVE_PREFIXES)

    def _mission_constraints(self, text: str) -> list[MissionConstraint]:
        normalized = normalize_text(text)
        constraints: list[MissionConstraint] = []
        pattern = re.compile(
            r"\b(?:nao|do not)\s+(?:inicialize|inicializar|initialize)\s+(?:um\s+)?(?:repositorio|repository)\s+(?:em|in)\s+([^\n.;]+)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(normalized):
            subject = match.group(1).strip().strip("`\"' ")
            if not subject:
                continue
            constraints.append(
                MissionConstraint(
                    constraint_id=f"git_init_deny_{self._digest(subject)}",
                    kind="git_init",
                    effect="deny",
                    subject=subject,
                    value=False,
                    source_ref="prompt_negative_git_init_scope",
                )
            )
        return constraints

    def _trim_locator(self, locator: str) -> str:
        return str(locator).strip().rstrip(".,;:!?)]}")

    def _digest(self, value: str) -> str:
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
