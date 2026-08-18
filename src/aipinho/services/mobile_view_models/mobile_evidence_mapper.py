from __future__ import annotations

from aipinho.schemas.mobile_view_models import EvidenceRef


class MobileEvidenceMapper:
    def ref(self, evidence_type: str, ref_id: str, label: str | None = None) -> EvidenceRef:
        return EvidenceRef(
            type=evidence_type,  # type: ignore[arg-type]
            ref_id=ref_id,
            human_label=label or f"{evidence_type}:{ref_id}",
            sanitized=True,
        )

    def endpoint_ref(self, endpoint: str, label: str | None = None) -> EvidenceRef:
        normalized = endpoint.replace("/", "_").strip("_") or "root"
        return self.ref("trace", f"endpoint:{normalized}", label or endpoint)

