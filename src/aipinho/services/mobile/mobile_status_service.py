from __future__ import annotations
from pathlib import Path
from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import inspect_yaml_file
from aipinho.services.mobile_view_models.mobile_view_model_service import MobileViewModelService
class MobileStatusService:
    CONFIGS=("config/mobile/mobile_app_policy.yaml","config/mobile/mobile_connection_policy.yaml","config/mobile/mobile_token_policy.yaml","config/mobile/mobile_realtime_policy.yaml","config/mobile/mobile_upload_policy.yaml","config/mobile/mobile_download_policy.yaml","config/mobile/mobile_debugger_policy.yaml","config/mobile/mobile_pipeline_policy.yaml","config/mobile/mobile_dashboard_policy.yaml","config/mobile/mobile_degraded_policy.yaml","config/mobile/mobile_security_policy.yaml")
    def status(self)->dict[str,object]:
        entries=[]; warnings=[]
        for rel in self.CONFIGS:
            st=inspect_yaml_file(PATHS.project_root/Path(rel),root=PATHS.project_root); entries.append(st.__dict__)
            if st.status!="ok": warnings.append(f"{rel}: {st.status}")
        mobile_view_model=MobileViewModelService().status()
        return {"status":"ok" if not warnings else "degraded","mobile_app_enabled":True,"android_app_enabled":True,"adb_reverse_supported":True,"wifi_lan_supported":True,"tailscale_supported":True,"manual_profile_supported":True,"token_hardcoded":False,"mobile_sync_via_backend":True,"bootstrap_control_port":9080,"mobile_restart_allowed_ports":[9088,9089,9098],"mobile_restart_blocked_ports":[9099],"mobile_monitor_restart_via_bootstrap":True,"raw_hidden_by_default":True,"unknown_event_normal_rendering":False,"mobile_view_models_enabled":mobile_view_model["mobile_view_models_enabled"],"mobile_humanization_enabled":mobile_view_model["mobile_humanization_enabled"],"mobile_evidence_mapping_enabled":mobile_view_model["mobile_evidence_mapping_enabled"],"mobile_safe_actions_enabled":mobile_view_model["mobile_safe_actions_enabled"],"mobile_copy_policy_enabled":mobile_view_model["mobile_copy_policy_enabled"],"mobile_phase_1_observability":mobile_view_model["mobile_phase_1_observability"],"mobile_phase_2_deep_evidence":mobile_view_model["mobile_phase_2_deep_evidence"],"mobile_phase_3_safe_operation":mobile_view_model["mobile_phase_3_safe_operation"],"mobile_phase_4_advanced_diagnostics":mobile_view_model["mobile_phase_4_advanced_diagnostics"],"mobile_phase_5_multimodal":mobile_view_model["mobile_phase_5_multimodal"],"ui_decides_policy":False,"ui_decides_safety":False,"ui_decides_final_status":False,"openapi_dump_as_ui":False,"configs":entries,"warnings":warnings}
