from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_draft import ArtifactDraft
from aipinho.schemas.artifacts.artifact_preview import ArtifactPreview
from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file

_SENSITIVE_KEYS = {"raw", "raw_content", "full_prompt", "prompt", "password", "secret", "token", "api_key"}


class ArtifactPreviewStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_store_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        configured = str((self.policy.get("store", {}) or {}).get("path", "data/runtime/artifact_previews"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_scanner = ArtifactSecretScanner()

    def save_draft(self, draft: ArtifactDraft) -> ArtifactDraft:
        self._write(self._draft_path(draft.draft_id), self._omit_source_content(draft.model_dump()))
        return draft

    def get_draft(self, draft_id: str) -> ArtifactDraft | None:
        data = self._read(self._draft_path(draft_id))
        return ArtifactDraft.model_validate(data) if data else None

    def save_preview(self, preview: ArtifactPreview) -> ArtifactPreview:
        self._write(self._preview_path(preview.preview_id), self._omit_source_content(preview.model_dump()))
        self.save_trace(preview.preview_id, preview.trace)
        return preview

    def get_preview(self, preview_id: str) -> ArtifactPreview | None:
        data = self._read(self._preview_path(preview_id))
        return ArtifactPreview.model_validate(data) if data else None

    def list_previews(self, *, status: str | None = None, source_type: str | None = None, risk_level: str | None = None, approval_status: str | None = None, limit: int = 100) -> list[ArtifactPreview]:
        previews: list[ArtifactPreview] = []
        root = self.root / "previews"
        if not root.exists():
            return []
        for path in root.glob("artifact_preview_*.json"):
            try:
                preview = ArtifactPreview.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                continue
            if status and preview.status != status:
                continue
            if source_type and preview.source.source_type != source_type:
                continue
            if risk_level and preview.risk.risk_level != risk_level:
                continue
            if approval_status and preview.approval_status != approval_status:
                continue
            previews.append(preview)
        return sorted(previews, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def save_trace(self, preview_id: str, trace: list[ArtifactTraceItem]) -> None:
        self._write(self._trace_path(preview_id), [item.model_dump() for item in trace])

    def get_trace(self, preview_id: str) -> list[ArtifactTraceItem]:
        data = self._read(self._trace_path(preview_id)) or []
        return [ArtifactTraceItem.model_validate(item) for item in data if isinstance(item, dict)]

    def update_preview_status(self, preview_id: str, status: str, *, approval_id: str | None = None, approval_status: str | None = None) -> ArtifactPreview:
        preview = self.get_preview(preview_id)
        if preview is None:
            raise ValueError("artifact_preview_not_found")
        preview.status = status  # type: ignore[assignment]
        if approval_id is not None:
            preview.approval_id = approval_id
        if approval_status is not None:
            preview.approval_status = approval_status
        from aipinho.services.session.session_store import utc_now
        preview.updated_at = utc_now()
        return self.save_preview(preview)

    def sanitize(self, value: Any, *, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS:
            return "[omitted_by_artifact_preview_store]"
        if isinstance(value, dict):
            return {str(k): self.sanitize(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            max_chars = int((self.policy.get("store", {}) or {}).get("max_saved_preview_chars", 20000))
            return self.secret_scanner.redact(value)[:max_chars]
        return value

    def _omit_source_content(self, value: dict[str, Any]) -> dict[str, Any]:
        source = value.get("source")
        if isinstance(source, dict) and source.get("content") is not None:
            source["content"] = "[omitted_by_artifact_preview_store]"
        return value

    def _draft_path(self, draft_id: str) -> Path:
        if not re.fullmatch(r"artifact_draft_[a-f0-9]+", draft_id):
            raise ValueError("invalid_artifact_draft_id")
        return resolve_within_root(self.root / "drafts" / f"{draft_id}.json", self.root)

    def _preview_path(self, preview_id: str) -> Path:
        if not re.fullmatch(r"artifact_preview_[a-f0-9]+", preview_id):
            raise ValueError("invalid_artifact_preview_id")
        return resolve_within_root(self.root / "previews" / f"{preview_id}.json", self.root)

    def _trace_path(self, preview_id: str) -> Path:
        if not re.fullmatch(r"artifact_preview_[a-f0-9]+", preview_id):
            raise ValueError("invalid_artifact_preview_id")
        return resolve_within_root(self.root / "traces" / f"{preview_id}.trace.json", self.root)

    def _write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.sanitize(value), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _read(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "artifact_preview_store", "path": str(self.root), "workspace_write_enabled": False, "sanitize_before_save": True}
