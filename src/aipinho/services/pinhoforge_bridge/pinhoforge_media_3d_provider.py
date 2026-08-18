from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.media_3d import (
    PinhoForge3DRequest,
    PinhoForge3DResult,
    PinhoForgeImageRequest,
    PinhoForgeImageResult,
    PinhoForgeMediaArtifact,
)
from aipinho.services.pinhoforge_bridge.workflow_context import workflow_evidence_refs
from aipinho.utils.yaml_loader import load_yaml_file


class PinhoForgeImageProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_media_3d.yaml"
        self.root = root or PATHS.project_root

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def list_capabilities(
        self,
        request_id: str = "pinhoforge_media_image_capabilities",
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PinhoForgeImageResult:
        image = self._image_config()
        return PinhoForgeImageResult(
            request_id=request_id,
            operation="list_capabilities",
            status="completed",
            human_message="Capacidades de imagem do PinhoForge listadas em modo governado.",
            capabilities=list(image.get("supported_operations") or []),
            supported_input_formats=list(image.get("supported_input_formats") or []),
            supported_output_formats=list(image.get("supported_output_formats") or []),
            evidence_refs=workflow_evidence_refs(metadata, ["provider:pinhoforge_media_3d", "module:image_lab"]),
        )

    def handle(self, request: PinhoForgeImageRequest) -> PinhoForgeImageResult:
        if request.operation == "list_capabilities":
            return self.list_capabilities(request.request_id, metadata=request.metadata)
        blocked = self._validate_image_request(request)
        if blocked is not None:
            return blocked
        input_path = Path(str(request.input_path)).expanduser()
        input_metadata = {
            "source_path_redacted": self._redact_path(input_path),
            "source_suffix": input_path.suffix.lower(),
            "size_bytes": input_path.stat().st_size,
        }
        if request.operation == "open_image":
            return PinhoForgeImageResult(
                request_id=request.request_id,
                operation=request.operation,
                status="completed",
                human_message="Imagem validada para operacao governada sem sobrescrever o original.",
                capabilities=list(self._image_config().get("supported_operations") or []),
                supported_input_formats=list(self._image_config().get("supported_input_formats") or []),
                supported_output_formats=list(self._image_config().get("supported_output_formats") or []),
                input_metadata=input_metadata,
                evidence_refs=self._image_evidence(request),
            )
        artifact = self._image_artifact(request)
        if artifact is None:
            return self._blocked_image(request, "image_artifact_output_missing", "Output validado de imagem nao foi encontrado.")
        review = self._review_decision(request)
        warnings = list(review.get("warnings") or [])
        report_json = {
            "request_id": request.request_id,
            "operation": request.operation,
            "source_scope": request.source_scope,
            "output_format": request.output_format,
            "operations_applied": [item.model_dump() for item in request.operations],
            "model_review_status": review.get("status"),
            "artifact_filename": artifact.filename,
        }
        report_markdown = self._image_report_markdown(request, artifact, review, input_metadata)
        return PinhoForgeImageResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed_with_warnings" if review.get("review_required_but_unavailable") else "completed",
            human_message="Imagem processada pelo provider governado e pronta para registro como artifact.",
            capabilities=list(self._image_config().get("supported_operations") or []),
            supported_input_formats=list(self._image_config().get("supported_input_formats") or []),
            supported_output_formats=list(self._image_config().get("supported_output_formats") or []),
            input_metadata=input_metadata,
            operations_applied=[item.model_dump() for item in request.operations],
            output_ref=f"artifact:{artifact.filename}",
            output_path_redacted=self._redact_path(Path(artifact.output_path_sanitized or artifact.filename)),
            artifact=artifact,
            artifacts=[artifact],
            report_markdown=report_markdown,
            report_json=report_json,
            model_review_recommended=bool(review.get("recommended")),
            model_review_result=review,
            warnings=warnings,
            evidence_refs=self._image_evidence(request) + [f"artifact:{artifact.filename}"],
        )

    def _validate_image_request(self, request: PinhoForgeImageRequest) -> PinhoForgeImageResult | None:
        image = self._image_config()
        allowed_scopes = set(str(item) for item in self._provider().get("allowed_source_scopes") or [])
        if request.source_scope not in allowed_scopes:
            return self._blocked_image(request, "image_external_path_unregistered", "Escopo de origem nao autorizado para operacoes de imagem.")
        if not request.input_path:
            return self._blocked_image(request, "image_input_path_required", "Arquivo de imagem obrigatorio.")
        input_path = Path(str(request.input_path)).expanduser()
        if not input_path.exists() or not input_path.is_file():
            return self._blocked_image(request, "image_input_not_found", "Arquivo de imagem nao encontrado.")
        suffix = input_path.suffix.lower().lstrip(".")
        if suffix not in {str(item).lower() for item in image.get("supported_input_formats") or []}:
            return self._blocked_image(request, "image_unsupported_input_format", "Formato de imagem nao suportado.")
        if request.operation in {"apply_operations", "export_image", "generate_report"}:
            if request.output_format.lower() not in {str(item).lower() for item in image.get("supported_output_formats") or []}:
                return self._blocked_image(request, "image_unsupported_export_format", "Formato de exportacao de imagem nao suportado.")
            if not request.bridge_output_path:
                return self._blocked_image(request, "image_artifact_output_required", "Execucao exige output validado retornado pelo provider.")
            output_path = Path(str(request.bridge_output_path)).expanduser()
            if output_path.resolve() == input_path.resolve():
                return self._blocked_image(request, "image_original_overwrite_blocked", "O original nao pode ser sobrescrito no bridge governado.")
        return None

    def _image_artifact(self, request: PinhoForgeImageRequest) -> PinhoForgeMediaArtifact | None:
        output = Path(str(request.bridge_output_path)).expanduser()
        if not output.exists() or not output.is_file():
            return None
        size = output.stat().st_size
        if size <= 0:
            return None
        filename = request.requested_output_name or output.name
        return PinhoForgeMediaArtifact(
            filename=filename,
            content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size_bytes=size,
            output_path_sanitized=str(output),
            status="ready",
        )

    def _image_report_markdown(
        self,
        request: PinhoForgeImageRequest,
        artifact: PinhoForgeMediaArtifact,
        review: dict[str, Any],
        input_metadata: dict[str, Any],
    ) -> str:
        return "\n".join(
            [
                "# PinhoForge Image Bridge Report",
                f"Request: {request.request_id}",
                f"Operation: {request.operation}",
                f"Source: {input_metadata['source_path_redacted']}",
                f"Output: {artifact.filename}",
                f"Review status: {review.get('status')}",
                "No visual quality claim was emitted without specialized review.",
            ]
        )

    def _review_decision(self, request: PinhoForgeImageRequest) -> dict[str, Any]:
        policy = request.model_review_policy.lower().strip()
        goal = str(request.metadata.get("review_goal") or "").lower()
        semantic = request.metadata.get("semantic_task") in {True, "true", "1"} or goal in {"aesthetic", "quality", "semantic", "ocr", "object_selection", "visual_judgement"}
        if policy == "required_always":
            return {
                "status": "review_required_but_unavailable",
                "recommended": True,
                "review_required_but_unavailable": True,
                "warnings": ["specialized_model_review_required"],
            }
        if policy == "required_for_semantic_tasks" and semantic:
            return {
                "status": "review_required_but_unavailable",
                "recommended": True,
                "review_required_but_unavailable": True,
                "warnings": ["specialized_model_review_required"],
            }
        if policy == "recommended" or semantic:
            return {
                "status": "review_recommended",
                "recommended": True,
                "review_required_but_unavailable": False,
                "warnings": ["specialized_model_review_recommended"] if semantic or policy == "recommended" else [],
            }
        return {
            "status": "review_not_requested",
            "recommended": False,
            "review_required_but_unavailable": False,
            "warnings": [],
        }

    def _blocked_image(self, request: PinhoForgeImageRequest, reason_code: str, message: str) -> PinhoForgeImageResult:
        return PinhoForgeImageResult(
            request_id=request.request_id,
            operation=request.operation,
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            evidence_refs=self._image_evidence(request),
        )

    def _image_evidence(self, request: PinhoForgeImageRequest) -> list[str]:
        refs = ["provider:pinhoforge_media_3d", "module:image_lab", f"request:{request.request_id}"]
        if request.input_artifact_id:
            refs.append(f"input_artifact:{request.input_artifact_id}")
        return workflow_evidence_refs(request.metadata, refs)

    def _image_config(self) -> dict[str, Any]:
        return dict(self._provider().get("image") or {})

    def _provider(self) -> dict[str, Any]:
        return dict(self.config().get("provider") or {})

    def _redact_path(self, path: Path) -> str:
        return str(path).replace(str(Path.home()), "C:\\Users\\<user>")


class PinhoForge3DProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_media_3d.yaml"
        self.root = root or PATHS.project_root

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def list_capabilities(
        self,
        request_id: str = "pinhoforge_media_3d_capabilities",
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PinhoForge3DResult:
        model = self._three_d_config()
        return PinhoForge3DResult(
            request_id=request_id,
            operation="list_capabilities",
            status="completed",
            human_message="Capacidades 3D do PinhoForge listadas em modo governado.",
            capabilities=list(model.get("supported_operations") or []),
            supported_export_formats=list(model.get("supported_export_formats") or []),
            evidence_refs=workflow_evidence_refs(metadata, ["provider:pinhoforge_media_3d", "module:3d_lab"]),
        )

    def handle(self, request: PinhoForge3DRequest) -> PinhoForge3DResult:
        if request.operation == "list_capabilities":
            return self.list_capabilities(request.request_id, metadata=request.metadata)
        blocked = self._validate_3d_request(request)
        if blocked is not None:
            return blocked
        artifact = None
        if request.operation in {"export_scene", "generate_report"} and request.bridge_output_path:
            artifact = self._scene_artifact(request)
            if artifact is None and request.operation == "export_scene":
                return self._blocked_3d(request, "scene_output_validation_failed", "Export 3D nao gerou arquivo valido.")
        scene_summary = {
            "scene_title": request.scene_title,
            "primitive_count": len(request.primitive_specs),
            "light_intensity": request.light_intensity,
            "camera_fov": request.camera_fov,
        }
        report_json = {
            "request_id": request.request_id,
            "scene_title": request.scene_title,
            "primitive_count": len(request.primitive_specs),
            "export_format": request.output_format if artifact else None,
        }
        report_markdown = "\n".join(
            [
                "# PinhoForge 3D Bridge Report",
                f"Request: {request.request_id}",
                f"Operation: {request.operation}",
                f"Scene: {request.scene_title}",
                f"Primitives: {len(request.primitive_specs)}",
                f"Artifact: {artifact.filename if artifact else 'not_exported'}",
            ]
        )
        return PinhoForge3DResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed",
            human_message="Cena 3D governada pronta para registro e supervisao.",
            capabilities=list(self._three_d_config().get("supported_operations") or []),
            supported_export_formats=list(self._three_d_config().get("supported_export_formats") or []),
            scene_id=f"scene_{request.request_id[-8:]}",
            scene_summary=scene_summary,
            primitives=[item.model_dump() for item in request.primitive_specs],
            export_format=request.output_format if artifact else None,
            output_ref=f"artifact:{artifact.filename}" if artifact else None,
            output_path_redacted=self._redact_path(Path(artifact.output_path_sanitized)) if artifact and artifact.output_path_sanitized else None,
            artifact=artifact,
            artifacts=[artifact] if artifact else [],
            report_markdown=report_markdown,
            report_json=report_json,
            evidence_refs=self._three_d_evidence(request) + ([f"artifact:{artifact.filename}"] if artifact else []),
        )

    def _validate_3d_request(self, request: PinhoForge3DRequest) -> PinhoForge3DResult | None:
        model = self._three_d_config()
        primitives = {str(item).lower() for item in model.get("supported_primitives") or []}
        exports = {str(item).lower() for item in model.get("supported_export_formats") or []}
        if request.metadata.get("external_asset_download") in {True, "true", "1"}:
            return self._blocked_3d(request, "media_external_asset_download_blocked", "Download de asset externo nao e permitido neste bridge.")
        for spec in request.primitive_specs:
            if spec.type.lower() not in primitives:
                return self._blocked_3d(request, "unsupported_3d_primitive", f"Primitiva 3D nao suportada: {spec.type}")
        if request.operation == "export_scene":
            if request.output_format.lower() not in exports:
                return self._blocked_3d(request, "unsupported_3d_export_format", "Formato de exportacao 3D nao suportado.")
            if not request.bridge_output_path:
                return self._blocked_3d(request, "scene_output_required", "Execucao 3D exige output validado retornado pelo provider.")
        return None

    def _scene_artifact(self, request: PinhoForge3DRequest) -> PinhoForgeMediaArtifact | None:
        output = Path(str(request.bridge_output_path)).expanduser()
        if not output.exists() or not output.is_file():
            return None
        size = output.stat().st_size
        if size <= 0:
            return None
        filename = request.requested_output_name or output.name
        return PinhoForgeMediaArtifact(
            filename=filename,
            content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size_bytes=size,
            output_path_sanitized=str(output),
            status="ready",
        )

    def _blocked_3d(self, request: PinhoForge3DRequest, reason_code: str, message: str) -> PinhoForge3DResult:
        return PinhoForge3DResult(
            request_id=request.request_id,
            operation=request.operation,
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            evidence_refs=self._three_d_evidence(request),
        )

    def _three_d_evidence(self, request: PinhoForge3DRequest) -> list[str]:
        return workflow_evidence_refs(
            request.metadata,
            ["provider:pinhoforge_media_3d", "module:3d_lab", f"request:{request.request_id}"],
        )

    def _three_d_config(self) -> dict[str, Any]:
        return dict((self.config().get("provider") or {}).get("three_d") or {})

    def _redact_path(self, path: Path) -> str:
        return str(path).replace(str(Path.home()), "C:\\Users\\<user>")
