from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class AgentRequestEnrichment:
    operation_type: str | None = None
    requested_capabilities: list[str] = field(default_factory=list)
    workspace_context: str | None = None
    target_paths: list[str] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)


class AgentRequestEnrichmentService:
    """Infers generic agent execution hints before provider/delegation routing.

    The service only enriches metadata used by policy/delegation. It does not
    execute tools and does not bypass the Tool Gateway.
    """

    def __init__(self, config_path=None, path_extractor: PathExtractionService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "agents" / "agent_request_enrichment.yaml"
        self.path_extractor = path_extractor or PathExtractionService()

    def config(self) -> dict[str, Any]:
        return load_yaml_file(self.config_path, critical=True, root=PATHS.config_root / "agents")

    def enrich(
        self,
        *,
        prompt: str,
        operation_type: str,
        requested_capabilities: list[str] | None = None,
        workspace_context: str | None = None,
        target_paths: list[str] | None = None,
    ) -> AgentRequestEnrichment:
        cfg = self.config()
        text = prompt.casefold()
        capabilities = list(requested_capabilities or [])
        targets = list(target_paths or [])
        evidence: list[dict[str, str]] = []
        selected_operation = operation_type

        extracted_paths = self.path_extractor.extract(prompt)
        if extracted_paths:
            text = self._text_without_extracted_paths(prompt, extracted_paths).casefold()
            for extracted in extracted_paths:
                if extracted.value not in targets:
                    targets.append(extracted.value)
            if not workspace_context:
                workspace_context = extracted_paths[0].value
                evidence.append({"type": "workspace_context", "source": "path_extraction"})
            for capability in cfg.get("default_workspace_capabilities") or []:
                capabilities.append(str(capability))

        for rule in cfg.get("rules") or []:
            markers = [str(marker).casefold() for marker in rule.get("markers") or []]
            matched = [marker for marker in markers if marker and self._marker_matches(text, marker)]
            if not matched:
                continue
            selected_operation = str(rule.get("operation_type") or selected_operation)
            for capability in rule.get("capabilities") or []:
                capabilities.append(str(capability))
            evidence.append({"type": "rule", "source": str(rule.get("id") or "unknown")})

        return AgentRequestEnrichment(
            operation_type=selected_operation,
            requested_capabilities=list(dict.fromkeys(capabilities)),
            workspace_context=workspace_context,
            target_paths=list(dict.fromkeys(targets)),
            evidence=evidence,
        )

    def _text_without_extracted_paths(self, prompt: str, extracted_paths: list[Any]) -> str:
        spans = sorted(((item.start, item.end) for item in extracted_paths), reverse=True)
        clean = prompt
        for start, end in spans:
            clean = f"{clean[:start]} <workspace_path> {clean[end:]}"
        return clean

    def _marker_matches(self, text: str, marker: str) -> bool:
        if not marker:
            return False
        if re.fullmatch(r"[\w-]+", marker, flags=re.UNICODE):
            return re.search(rf"(?<![\w-]){re.escape(marker)}(?![\w-])", text, flags=re.UNICODE) is not None
        return marker in text
