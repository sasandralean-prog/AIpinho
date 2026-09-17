from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from aipinho.services.governance.intent.intent_normalizer import normalize_text


@dataclass(frozen=True)
class ExplicitHumanAuthorityResolution:
    requested_capabilities: list[str]
    authorized_capabilities: list[str]
    evidence: list[dict[str, object]]


class IntentHumanAuthorityService:
    """Extracts explicit human authorization at semantic ingress only.

    Mentioned/imperative capability and explicit consent stay separate. Runtime
    gates consume frozen evidence; they never reparse the prompt.
    """

    _GRANT_RE = re.compile(
        r"\b(?:eu\s+)?(?:autorizo|permito|concedo\s+permissao|dou\s+permissao)\b",
        re.IGNORECASE,
    )
    _NEGATED_GRANT_RE = re.compile(
        r"\bnao\s+(?:autorizo|permito|concedo\s+permissao|dou\s+permissao)\b",
        re.IGNORECASE,
    )

    _CAPABILITY_MARKERS: dict[str, tuple[str, ...]] = {
        "read_file": ("leitura", "ler", "read", "diagnostico", "diagnóstico", "inspecao", "inspeção"),
        "list_files": ("leitura", "listar", "inventariar", "read", "diagnostico", "diagnóstico"),
        "copy_from": ("copiar", "copy"),
        "create_directory": ("criar diretorio", "criar diretório", "criar pasta", "diretorios", "diretórios"),
        "create_file": ("criar arquivo", "criacao de arquivo", "criação de arquivo", "escrita"),
        "modify_file": ("editar", "edicao", "edição", "alterar", "modificar", "mudanca", "mudança", "codigo", "código"),
        "apply_patch": ("patch", "editar", "edicao", "edição", "alterar", "modificar", "codigo", "código"),
        "artifact_create": ("artefato", "artifact"),
        "shell_readonly": ("shell", "comando"),
        "shell_build": ("gradle", "build", "compile", "compilar", "compilacao", "compilação"),
        "shell_test": ("test", "teste", "testes", "regressao", "regressão"),
        "script_execution": ("executar aplicativo", "executar app", "rodar aplicativo", "rodar app", "execucao controlada", "execução controlada"),
        "network_download": ("network", "internet", "rede", "download"),
        "git_clone": ("git clone", "clone", "clonar"),
        "git_fetch": ("git fetch", "fetch"),
        "git_pull_ff": ("git pull", "pull fast-forward", "pull --ff-only"),
        "git_commit": ("git commit", "commit"),
        "git_push": ("git push", "push"),
    }

    def resolve(
        self,
        *,
        prompt: str,
        known_capabilities: list[str],
    ) -> ExplicitHumanAuthorityResolution:
        text = str(prompt or "")
        prompt_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        normalized = normalize_text(text)
        requested = sorted(
            capability
            for capability in set(known_capabilities)
            if self._mentions(normalized, capability)
        )
        if "network_download" not in requested and self._mentions(normalized, "network_download"):
            requested.append("network_download")
            requested.sort()

        authorized: set[str] = set()
        evidence: list[dict[str, object]] = []
        for clause in self._authorization_clauses(text):
            normalized_clause = normalize_text(clause)
            clause_caps = sorted(
                capability
                for capability in set([*known_capabilities, "network_download"])
                if self._mentions(normalized_clause, capability)
            )
            if not clause_caps:
                continue
            authorized.update(clause_caps)
            digest = hashlib.sha256(clause.encode("utf-8")).hexdigest()
            evidence.append({
                "kind": "explicit_human_authorization",
                "source_ref": f"prompt_authority:{digest[:20]}",
                "clause_sha256": digest,
                "source_prompt_sha256": prompt_sha256,
                "capabilities": clause_caps,
            })

        return ExplicitHumanAuthorityResolution(
            requested_capabilities=requested,
            authorized_capabilities=sorted(authorized),
            evidence=evidence,
        )

    def _authorization_clauses(self, text: str) -> list[str]:
        clauses: list[str] = []
        segments = re.split(r"(?<=[.!?])\s+|\n\s*\n", text or "")
        for segment in segments:
            normalized = normalize_text(segment)
            if not normalized or self._NEGATED_GRANT_RE.search(normalized):
                continue
            if self._GRANT_RE.search(normalized):
                clauses.append(segment.strip())
        return clauses

    def _mentions(self, normalized_text: str, capability: str) -> bool:
        markers = self._CAPABILITY_MARKERS.get(capability, ())
        padded = f" {normalized_text} "
        return any(normalize_text(marker) in padded for marker in markers)
