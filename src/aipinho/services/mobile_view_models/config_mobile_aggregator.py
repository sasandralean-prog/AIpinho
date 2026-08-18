from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileConfigViewModel, MobileScreenState
from aipinho.services.config_governance.config_governance_service import ConfigGovernanceService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder


class ConfigMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()
        self.actions = MobileSafeActionBuilder()

    def view_model(self) -> MobileConfigViewModel:
        governance_health = self._governance_health()
        permission_summary = self._permission_summary()
        cards = [
            self.cards.card(
                card_id="config_connection",
                screen="config",
                card_type="connection",
                title="Conexao e Pairing",
                status="healthy",
                severity="success",
                happening="Config mostra perfis, pairing, ADB reverse, Wi-Fi e Tailscale.",
                why="Conectividade vem de endpoints backend, nao de sincronizacao direta com launcher.",
                safety="safe",
                safety_reason="Teste de conexao e leitura segura; token nao aparece.",
                actions=["Testar conexao.", "Ver comandos ADB.", "Rotacionar token via fluxo oficial."],
                evidence=[self.evidence.ref("trace", "connection_profiles", "connection profiles")],
                metadata={"token_visible": False, "sync_source": "backend"},
            ),
            self.cards.card(
                card_id="config_capabilities",
                screen="config",
                card_type="capabilities",
                title="Capabilities e Modulos",
                status="healthy",
                severity="info",
                happening="Config mostra capabilities, roles, models, tools e skills.",
                why="O backend e fonte de verdade sobre permissoes e modulos ativos.",
                safety="safe",
                safety_reason="A tela nao concede capability; apenas renderiza.",
                actions=["Abrir Models/Roles.", "Abrir Skills/Tools.", "Copiar capacidades."],
                evidence=[self.evidence.ref("policy_decision", "capability_registry", "capability registry")],
                metadata={"ui_decides_policy": False},
            ),
            self.cards.card(
                card_id="config_rag_memory",
                screen="config",
                card_type="rag_memory",
                title="RAG/Memory Namespaces",
                status="degraded",
                severity="warning",
                happening="RAG e Memory aparecem como namespaces e policy.",
                why="Legacy RAG e historico/diagnostico; memoria curada exige approval humano.",
                safety="caution",
                safety_reason="Evita tratar chunk legado como verdade atual.",
                actions=["Abrir evidencia.", "Copiar status.", "Ver conflitos legacy."],
                evidence=[self.evidence.ref("memory_evidence", "curated", "curated memory")],
                metadata={"legacy_current_truth_allowed": False},
            ),
            self.cards.card(
                card_id="config_governance",
                screen="config",
                card_type="governance",
                title="Governanca Configuravel",
                status="healthy" if governance_health.get("status") == "ok" else "degraded",
                severity="info" if governance_health.get("status") == "ok" else "warning",
                happening="Config Governance expõe policies, providers, workspaces, backups e mudanças pendentes por API.",
                why="A UI deve pedir preview/diff/approval/apply no backend; ela nunca edita arquivos de config diretamente.",
                safety="safe",
                safety_reason="Mutacoes exigem token local e passam por ConfigChangeRequest.",
                actions=["Ver effective policy.", "Ver backups.", "Abrir mudanças pendentes."],
                evidence=[self.evidence.ref("policy_decision", "config_governance", "config governance")],
                metadata={
                    "health_status": str(governance_health.get("status", "unknown")),
                    "pending_changes": str(governance_health.get("pending_changes", 0)),
                    "backups": str(governance_health.get("backups", 0)),
                },
                safe_actions=[
                    self.actions.navigate("open_effective_policy", "Effective policy", "/api/v1/config/effective-policy"),
                    self.actions.navigate("open_config_changes", "Mudancas", "/api/v1/config/changes"),
                ],
            ),
            self.cards.card(
                card_id="config_workspace_matrix",
                screen="config",
                card_type="workspace_permission_matrix",
                title="Workspace Registry e Permission Matrix",
                status="healthy" if permission_summary.get("status") == "ok" else "degraded",
                severity="info" if permission_summary.get("status") == "ok" else "warning",
                happening="Workspaces usam longest-path match, roles e permissões allow/ask/deny do backend.",
                why="Fluxos multi-workspace dependem dessa matriz para leitura, escrita, shell, artifacts e transferência.",
                safety="safe",
                safety_reason="A tela renderiza a matriz; permissões efetivas são calculadas no backend.",
                actions=["Ver workspaces.", "Ver roles.", "Ver matrix."],
                evidence=[self.evidence.ref("policy_decision", "workspace_permission_matrix", "workspace permission matrix")],
                metadata={
                    "workspace_count": str(permission_summary.get("workspace_count", 0)),
                    "role_count": str(permission_summary.get("role_count", 0)),
                },
                safe_actions=[
                    self.actions.navigate("open_workspaces", "Workspaces", "/api/v1/config/workspaces"),
                    self.actions.navigate("open_permission_matrix", "Permission matrix", "/api/v1/config/permission-matrix"),
                ],
            ),
            self.cards.card(
                card_id="config_workspace_flows",
                screen="config",
                card_type="workspace_flows",
                title="Flow Rules Multi-Workspace",
                status="healthy",
                severity="info",
                happening="Fluxos copy/move/import/download/apply/delete/git_push são planejados antes de executar.",
                why="Cada plano separa fonte e destino, cria approval quando policy pede e bloqueia denies com motivo rastreável.",
                safety="safe",
                safety_reason="Move é copy + validate + delete; git_push exige approval; download vai para staging.",
                actions=["Listar regras.", "Criar preview.", "Abrir plans por run."],
                evidence=[self.evidence.ref("policy_decision", "workspace_flow_rules", "workspace flow rules")],
                metadata={"raw_default_visible": "false", "ui_executes_flow": "false"},
                safe_actions=[
                    self.actions.navigate("open_workspace_flow_rules", "Flow rules", "/api/v1/workspace-flows/rules"),
                ],
            ),
        ]
        return MobileConfigViewModel(
            state=MobileScreenState(
                screen="config",
                status="healthy",
                human_summary="Config humano carregado com conexao, pairing, capabilities, modules, RAG e Memory.",
            ),
            cards=cards,
            capabilities={
                "mobile_view_models_enabled": True,
                "mobile_humanization_enabled": True,
                "mobile_evidence_mapping_enabled": True,
                "mobile_safe_actions_enabled": True,
                "mobile_copy_policy_enabled": True,
                "ui_decides_policy": False,
                "config_governance_enabled": True,
                "workspace_permission_matrix_enabled": True,
                "workspace_flow_rules_enabled": True,
            },
            trace_id="mobile_vm_config",
        )

    def _governance_health(self) -> dict[str, object]:
        try:
            return ConfigGovernanceService().health()
        except Exception as exc:  # pragma: no cover - defensive mobile degraded state
            return {"status": "degraded", "error": exc.__class__.__name__}

    def _permission_summary(self) -> dict[str, object]:
        try:
            matrix = WorkspacePermissionMatrixService().load()
            return {
                "status": "ok",
                "workspace_count": len(matrix.list_workspaces()),
                "role_count": len(matrix.role_defaults()),
            }
        except Exception as exc:  # pragma: no cover - defensive mobile degraded state
            return {"status": "degraded", "error": exc.__class__.__name__}
