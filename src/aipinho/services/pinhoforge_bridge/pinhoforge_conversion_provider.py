from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.conversion import (
    PinhoForgeConversionArtifact,
    PinhoForgeConversionRequest,
    PinhoForgeConversionResult,
)
from aipinho.services.pinhoforge_bridge.workflow_context import workflow_evidence_refs
from aipinho.utils.yaml_loader import load_yaml_file


class PinhoForgeConversionProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_conversion.yaml"
        self.root = root or PATHS.project_root

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def list_capabilities(
        self,
        request_id: str = "pinhoforge_conversion_capabilities",
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PinhoForgeConversionResult:
        provider = self.config().get("provider") or {}
        capabilities = list(provider.get("capabilities") or [])
        return PinhoForgeConversionResult(
            request_id=request_id,
            operation="list_capabilities",
            status="completed",
            human_message="Capacidades de conversao do PinhoForge listadas em modo governado.",
            capabilities=capabilities,
            evidence_refs=self._evidence(request_id, metadata),
        )

    def dry_run(self, request: PinhoForgeConversionRequest) -> PinhoForgeConversionResult:
        block = self._policy_block(request, require_output=False)
        if block:
            return block
        route = self._route(request)
        return PinhoForgeConversionResult(
            request_id=request.request_id,
            operation="dry_run",
            status="preview_created",
            human_message="Preview de conversao criado sem gerar output.",
            route=route,
            dry_run={
                "created_output": False,
                "target_format": request.target_format,
                "detected_format": request.detected_format,
                "source_scope": request.source_scope,
                "requires_artifact_registration": True,
            },
            evidence_refs=self._evidence(request.request_id, request.metadata),
        )

    def execute(self, request: PinhoForgeConversionRequest) -> PinhoForgeConversionResult:
        block = self._policy_block(request, require_output=True)
        if block:
            return block
        output = Path(str(request.bridge_output_path)).expanduser()
        if not output.exists() or not output.is_file():
            return self._blocked(request, "validated_output_missing", "Output validado do provider nao foi encontrado.")
        size = output.stat().st_size
        if size <= 0:
            return self._blocked(request, "validated_output_empty", "Output validado do provider esta vazio.")
        filename = request.requested_output_name or output.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return PinhoForgeConversionResult(
            request_id=request.request_id,
            operation="execute",
            status="completed",
            human_message="Conversao validada pelo provider e pronta para registro como artifact.",
            route=self._route(request),
            artifact=PinhoForgeConversionArtifact(
                filename=filename,
                content_type=content_type,
                size_bytes=size,
                output_path_sanitized=str(output),
                status="ready",
            ),
            evidence_refs=self._evidence(request.request_id, request.metadata),
        )

    def _policy_block(self, request: PinhoForgeConversionRequest, *, require_output: bool) -> PinhoForgeConversionResult | None:
        provider = self.config().get("provider") or {}
        allowed_scopes = set(str(item) for item in provider.get("allowed_source_scopes") or [])
        if request.source_scope not in allowed_scopes:
            return self._blocked(request, "source_scope_not_allowed", "Escopo de origem nao autorizado para conversao.")
        if request.allow_semantic_conversion and not bool(provider.get("allow_semantic_conversion", False)):
            return self._blocked(request, "semantic_conversion_disabled", "Conversao semantica esta desabilitada por policy.")
        if request.allow_experimental_conversion and not bool(provider.get("allow_experimental_conversion", False)):
            return self._blocked(request, "experimental_conversion_disabled", "Conversao experimental esta desabilitada por policy.")
        if require_output and not request.bridge_output_path:
            return self._blocked(request, "validated_output_required", "Execucao exige output validado retornado pelo provider.")
        if request.input_path:
            input_path = Path(request.input_path).expanduser()
            if not input_path.exists() or not input_path.is_file():
                return self._blocked(request, "input_file_not_found", "Arquivo de entrada ausente ou invalido.")
        return None

    def _route(self, request: PinhoForgeConversionRequest) -> dict[str, Any]:
        return {
            "provider_id": "pinhoforge_studio",
            "detected_format": request.detected_format,
            "target_format": request.target_format,
            "source_scope": request.source_scope,
            "execution_model": "provider_validated_output",
            "artifact_registration_required": True,
        }

    def _blocked(self, request: PinhoForgeConversionRequest, reason_code: str, message: str) -> PinhoForgeConversionResult:
        return PinhoForgeConversionResult(
            request_id=request.request_id,
            operation=request.operation,
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            evidence_refs=self._evidence(request.request_id, request.metadata),
        )

    def _evidence(self, request_id: str, metadata: dict[str, Any] | None) -> list[str]:
        return workflow_evidence_refs(metadata, ["provider:pinhoforge_conversion", f"request:{request_id}"])
