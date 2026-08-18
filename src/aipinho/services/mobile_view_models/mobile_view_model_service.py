from __future__ import annotations

from aipinho.schemas.mobile_view_models import (
    EvidenceBundleView,
    MobileChatViewModel,
    MobileConfigViewModel,
    MobileDashboardViewModel,
    MobileDebuggerViewModel,
    MobilePipelineViewModel,
    MobileSupportBundlePreview,
    SanitizedCopyPayload,
)
from aipinho.services.mobile_view_models.chat_mobile_aggregator import ChatMobileAggregator
from aipinho.services.mobile_view_models.config_mobile_aggregator import ConfigMobileAggregator
from aipinho.services.mobile_view_models.dashboard_mobile_aggregator import DashboardMobileAggregator
from aipinho.services.mobile_view_models.debugger_mobile_aggregator import DebuggerMobileAggregator
from aipinho.services.mobile_view_models.evidence_mobile_aggregator import EvidenceMobileAggregator
from aipinho.services.mobile_view_models.mobile_copy_payload_service import MobileCopyPayloadService
from aipinho.services.mobile_view_models.mobile_endpoint_inventory_service import MobileEndpointInventoryService
from aipinho.services.mobile_view_models.pipeline_mobile_aggregator import PipelineMobileAggregator
from aipinho.services.mobile_view_models.support_bundle_mobile_aggregator import SupportBundleMobileAggregator


class MobileViewModelService:
    def status(self) -> dict[str, object]:
        inventory = MobileEndpointInventoryService().inventory()
        return {
            "status": "ok",
            "mobile_view_models_enabled": True,
            "mobile_humanization_enabled": True,
            "mobile_evidence_mapping_enabled": True,
            "mobile_safe_actions_enabled": True,
            "mobile_copy_policy_enabled": True,
            "mobile_phase_1_observability": True,
            "mobile_phase_2_deep_evidence": True,
            "mobile_phase_3_safe_operation": True,
            "mobile_phase_4_advanced_diagnostics": True,
            "mobile_phase_5_multimodal": True,
            "ui_decides_policy": False,
            "ui_decides_safety": False,
            "ui_decides_final_status": False,
            "raw_default_visible": False,
            "openapi_dump_as_ui": False,
            "endpoint_inventory": inventory,
        }

    def dashboard(self) -> MobileDashboardViewModel:
        return DashboardMobileAggregator().view_model()

    def chat(self, session_id: str) -> MobileChatViewModel:
        return ChatMobileAggregator().view_model(session_id)

    def pipeline(self, task_id: str | None = None) -> MobilePipelineViewModel:
        return PipelineMobileAggregator().view_model(task_id)

    def debugger(self) -> MobileDebuggerViewModel:
        return DebuggerMobileAggregator().view_model()

    def debugger_trace(self, trace_id: str) -> MobileDebuggerViewModel:
        return DebuggerMobileAggregator().view_model(trace_id)

    def config(self) -> MobileConfigViewModel:
        return ConfigMobileAggregator().view_model()

    def evidence(self, evidence_type: str, ref_id: str) -> EvidenceBundleView:
        return EvidenceMobileAggregator().view_model(evidence_type, ref_id)

    def support_bundle_preview(self) -> MobileSupportBundlePreview:
        return SupportBundleMobileAggregator().preview()

    def copy_card(self, card_id: str) -> SanitizedCopyPayload:
        for screen in (self.dashboard(), self.chat("latest"), self.pipeline(), self.debugger(), self.config()):
            for card in screen.cards:
                if card.card_id == card_id:
                    return MobileCopyPayloadService().payload_for_card(card)
        raise KeyError(card_id)

    def copy_raw(self, raw_ref: str) -> dict[str, object]:
        return {
            "ok": True,
            "raw_ref": raw_ref,
            "copy_policy": "sanitized_only",
            "summary": "Raw disponivel apenas por referencia e sanitizado pelo backend.",
            "raw_default_visible": False,
        }

    def refresh(self) -> dict[str, object]:
        return {"ok": True, "status": "refreshed", "side_effect": False}

