from __future__ import annotations

from aipinho.schemas.templates import AssetManifest
from aipinho.services.sandbox.project_templates.asset_placeholders import vector_placeholder_xml


class AssetPlaceholderGenerator:
    def vector_xml(self, *, label: str, color: str = "#22d3ee", shape: str = "rect", template_id: str | None = None) -> tuple[str, AssetManifest]:
        filename = f"{self._safe_name(label)}.xml"
        content = vector_placeholder_xml(label=label, color=color, shape=shape)
        manifest = AssetManifest(
            display_name=label,
            filename=filename,
            asset_type="vector_drawable",
            format="xml",
            generated=True,
            source="local_placeholder_generator",
            size_bytes=len(content.encode("utf-8")),
            usage="template_placeholder",
            template_id=template_id,
            metadata_sanitized={"shape": shape, "color": color},
        )
        return content, manifest

    def _safe_name(self, value: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
        return safe or "placeholder"
