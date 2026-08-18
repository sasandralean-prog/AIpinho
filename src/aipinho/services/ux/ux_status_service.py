from __future__ import annotations
from pathlib import Path
from aipinho.core.paths import PATHS
from aipinho.schemas.ux.ux_status import UXStatus
from aipinho.utils.yaml_loader import inspect_yaml_file
class UXStatusService:
    POLICY_FILES=("config/ux/ux_hardening_policy.yaml","config/ux/degraded_state_policy.yaml","config/ux/notification_policy.yaml","config/ux/human_error_policy.yaml","config/ux/latency_indicator_policy.yaml","config/ux/progress_indicator_policy.yaml","config/ux/copy_action_hardening_policy.yaml","config/ux/session_recovery_policy.yaml","config/ux/approval_clarity_policy.yaml","config/events/event_filter_policy.yaml","config/events/event_search_policy.yaml","config/interaction/raw_viewer_policy.yaml","config/transfers/upload_progress_policy.yaml","config/transfers/download_manager_policy.yaml","config/transfers/transfer_integrity_policy.yaml","config/launcher/desktop_ui_hardening_policy.yaml","config/launcher/desktop_ui_reconnect_policy.yaml","config/launcher/desktop_ui_notification_policy.yaml")
    def status(self) -> UXStatus:
        loaded=[]; warnings=[]
        for relative in self.POLICY_FILES:
            status=inspect_yaml_file(PATHS.project_root/Path(relative),root=PATHS.project_root)
            (loaded if status.status=="ok" else warnings).append(relative if status.status=="ok" else f"{relative}: {status.status}")
        features={"ux_hardening_enabled":True,"degraded_states_enabled":True,"reconnect_enabled":True,"fallback_polling_enabled":True,"download_manager_enabled":True,"upload_progress_enabled":True,"raw_viewer_enabled":True,"event_filters_enabled":True,"session_recovery_enabled":True,"token_redaction_enabled":True,"maintenance_plane_enabled":True,"supervised_autocure_enabled":True,"autonomous_apply":False,"replay_harness_enabled":True,"regression_harness_enabled":True,"replay_side_effects_allowed":False,"regression_side_effects_allowed":False}
        return UXStatus(status="ok" if not warnings else "degraded",enabled=True,hardening_policies_loaded=loaded,features=features,warnings=warnings)
