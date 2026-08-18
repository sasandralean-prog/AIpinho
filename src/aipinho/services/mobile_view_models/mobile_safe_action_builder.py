from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.mobile_view_models import SafeUiAction
from aipinho.utils.yaml_loader import load_yaml_file


class MobileSafeActionBuilder:
    def __init__(self) -> None:
        policy_path = PATHS.config_root / "mobile" / "mobile_safe_action_policy.yaml"
        self.policy = load_yaml_file(policy_path, critical=False, root=PATHS.project_root)

    def _restart_ports(self, key: str) -> set[int]:
        restart_ports = self.policy.get("restart_ports", {})
        values = restart_ports.get(key, []) if isinstance(restart_ports, dict) else []
        return {int(value) for value in values}

    def copy(self, card_id: str) -> SafeUiAction:
        return SafeUiAction(
            action_id=f"copy_{card_id}",
            label="Copiar resumo",
            kind="copy",
            endpoint_ref=f"/api/v1/mobile/view-model/cards/{card_id}/copy",
            method="POST",
            human_explanation="Copia somente o resumo sanitizado do card.",
        )

    def refresh(self, screen: str) -> SafeUiAction:
        return SafeUiAction(
            action_id=f"refresh_{screen}",
            label="Atualizar",
            kind="refresh",
            endpoint_ref="/api/v1/mobile/view-model/refresh",
            method="POST",
            human_explanation="Recarrega o view-model sem executar acao operacional.",
        )

    def navigate(self, action_id: str, label: str, endpoint_ref: str) -> SafeUiAction:
        return SafeUiAction(
            action_id=action_id,
            label=label,
            kind="navigate",
            endpoint_ref=endpoint_ref,
            human_explanation="Abre uma visao sanitizada relacionada.",
        )

    def open_trace(self, trace_id: str) -> SafeUiAction:
        return SafeUiAction(
            action_id=f"open_trace_{trace_id}",
            label="Abrir trace",
            kind="open_trace",
            endpoint_ref=f"/api/v1/mobile/view-model/debugger/trace/{trace_id}",
            human_explanation="Abre o trace em modo leitura sanitizada.",
        )

    def restart_port(self, port: int) -> SafeUiAction:
        allowed = port in self._restart_ports("allowed")
        blocked = port in self._restart_ports("blocked")
        enabled = allowed and not blocked
        return SafeUiAction(
            action_id=f"restart_{port}",
            label=f"Reiniciar {port}",
            kind="restart_port",
            risk="medium" if enabled else "critical",
            requires_confirmation=True,
            enabled=enabled,
            disabled_reason=None if enabled else "Porta bloqueada pela mobile_safe_action_policy.",
            endpoint_ref=f"/api/v1/monitor/ports/{port}/restart",
            method="POST",
            side_effect=True,
            human_explanation="Restart permitido somente para portas liberadas por policy." if enabled else "Restart bloqueado pelo backend aggregator/policy.",
        )

    def restart_backend(self) -> SafeUiAction:
        return SafeUiAction(
            action_id="restart_core_backend",
            label="Reiniciar backend",
            kind="restart_backend",
            risk="medium",
            requires_confirmation=True,
            requires_approval=False,
            enabled=True,
            endpoint_ref="/api/v1/backend-control/restart",
            method="POST",
            side_effect=True,
            human_explanation="Reinicia somente o backend principal pelos scripts canonicos via porta de controle 9099.",
        )

    def restart_monitor_via_bootstrap(self) -> SafeUiAction:
        actions = self.policy.get("allowed_actions", [])
        enabled = "restart_monitor_via_bootstrap" in actions if isinstance(actions, list) else False
        return SafeUiAction(
            action_id="restart_monitor_9099_via_9080",
            label="Reiniciar monitor 9099",
            kind="restart_monitor_via_bootstrap",
            risk="medium" if enabled else "critical",
            requires_confirmation=True,
            requires_approval=False,
            enabled=enabled,
            disabled_reason=None if enabled else "Bootstrap 9080 nao esta liberado pela mobile_safe_action_policy.",
            endpoint_ref="/api/v1/bootstrap-control/monitor/restart",
            method="POST",
            side_effect=True,
            human_explanation="Reinicia somente o monitor 9099 pelo canal bootstrap 9080; nao executa shell livre.",
        )

    def support_bundle_preview(self) -> SafeUiAction:
        return SafeUiAction(
            action_id="support_bundle_preview",
            label="Preview support bundle",
            kind="create_support_bundle",
            risk="low",
            endpoint_ref="/api/v1/mobile/view-model/support-bundle/preview",
            human_explanation="Gera apenas preview sanitizado; nao coleta raw inseguro.",
        )

    def disabled(self, action_id: str, label: str, reason: str) -> SafeUiAction:
        return SafeUiAction(
            action_id=action_id,
            label=label,
            kind="navigate",
            enabled=False,
            disabled_reason=reason,
            endpoint_ref="policy:block",
            human_explanation=reason,
        )
