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
        "copy_from": ("copiar", "copie", "copy"),
        "create_directory": (
            "criar diretorio",
            "criar diretório",
            "crie diretorio",
            "crie diretório",
            "criar pasta",
            "crie pasta",
        ),
        "create_file": (
            "criar arquivo",
            "crie arquivo",
            "criacao de arquivo",
            "criação de arquivo",
            "criacao/alteracao de teste",
            "criação/alteração de teste",
            "criacao e alteracao de teste",
            "criação e alteração de teste",
            "criar teste",
            "crie teste",
            "adicionar teste",
            "adicione teste",
        ),
        "modify_file": ("editar", "edicao", "edição", "alterar", "modificar", "mudanca", "mudança", "codigo", "código"),
        "apply_patch": ("patch", "editar", "edicao", "edição", "alterar", "modificar", "codigo", "código"),
        "artifact_create": (
            "criar artefato",
            "crie artefato",
            "gerar artefato",
            "gere artefato",
            "salvar artefato",
            "criar artifact",
            "generate artifact",
        ),
        "shell_readonly": (
            "executar comando",
            "execute comando",
            "rodar comando",
            "rode comando",
            "shell",
            "diagnostico",
            "diagnóstico",
            "preflight",
        ),
        "shell_build": ("gradle", "build", "compile", "compilar", "compilacao", "compilação"),
        "shell_test": ("test", "teste", "testes", "regressao", "regressão"),
        "script_execution": ("executar aplicativo", "executar app", "rodar aplicativo", "rodar app", "execucao controlada", "execução controlada"),
        "network_download": ("network", "internet", "rede", "download"),
        "git_clone": ("git clone", "clone", "clonar", "copia git limpa", "cópia git limpa"),
        "git_fetch": ("git fetch", "fetch"),
        "git_pull_ff": ("git pull", "pull fast-forward", "pull --ff-only", "fast-forward", "fast forward", "ff-only"),
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
        candidates = set([*known_capabilities, "network_download"])
        requested = sorted(
            capability
            for capability in candidates
            if self._mentions_positive(text, capability)
        )

        authorized: set[str] = set()
        evidence: list[dict[str, object]] = []
        for clause in self._authorization_clauses(text):
            clause_caps = sorted(
                capability
                for capability in candidates
                if self._mentions_positive(clause, capability)
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

    def _mentions_positive(self, text: str, capability: str) -> bool:
        normalized = normalize_text(text)
        for marker in self._CAPABILITY_MARKERS.get(capability, ()):
            normalized_marker = normalize_text(marker)
            if not normalized_marker:
                continue
            start = 0
            while True:
                index = normalized.find(normalized_marker, start)
                if index < 0:
                    break
                if not self._mention_is_directly_negated(
                    normalized,
                    marker_start=index,
                ):
                    return True
                start = index + max(1, len(normalized_marker))
        return False

    def _mention_is_directly_negated(
        self,
        normalized_text: str,
        *,
        marker_start: int,
    ) -> bool:
        prefix = normalized_text[max(0, marker_start - 72):marker_start]
        return bool(
            re.search(
                r"\b(?:nao|nunca|sem)\b(?:\s+[0-9a-z_./+-]+){0,4}\s*$",
                prefix,
            )
        )
