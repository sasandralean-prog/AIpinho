from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileDashboardViewModel, MobileScreenState
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.projects.project_profile_registry_service import ProjectProfileRegistryService
from aipinho.services.maintenance.maintenance_core import MaintenancePlaneService
from aipinho.services.realtime.realtime_status_service import RealtimeStatusService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService
from aipinho.services.supervisor.backend_control_service import BackendControlService
from aipinho.services.supervisor.bootstrap_control_service import BootstrapControlService


class DashboardMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()
        self.actions = MobileSafeActionBuilder()

    def view_model(self) -> MobileDashboardViewModel:
        backend_status = BackendControlService().status()
        bootstrap_status = BootstrapControlService().status()
        realtime_status = RealtimeStatusService().status()
        realtime_is_ok = realtime_status.get("status") == "ok" and bool(realtime_status.get("enabled"))
        maintenance_status = MaintenancePlaneService().status()
        maintenance_is_ok = maintenance_status.status == "ok"
        backend_severity = {
            "online": "success",
            "restarting": "warning",
            "degraded": "warning",
            "offline": "danger",
        }.get(backend_status.status, "unknown")
        backend_card_status = {
            "online": "healthy",
            "restarting": "running",
            "degraded": "degraded",
            "offline": "offline",
        }.get(backend_status.status, "unknown")
        cards = [
            self.cards.card(
                card_id="dashboard_backend_control",
                screen="dashboard",
                card_type="backend_control_status",
                title="Backend",
                status=backend_card_status,
                severity=backend_severity,
                happening=backend_status.human_message,
                why="A porta 9099 observa e reinicia a 9088; a porta 9080 e o bootstrap minimo que pode reerguer o 9099 quando ele cair.",
                safety="caution" if backend_status.status in {"restarting", "offline", "degraded"} else "safe",
                safety_reason="Restart e side effect controlado por token, policy e scripts canonicos.",
                actions=["Atualizar status.", "Reiniciar backend pelos scripts canonicos.", "Reiniciar monitor 9099 pelo bootstrap 9080.", "Copiar resumo sanitizado."],
                evidence=[
                    self.evidence.ref("monitor", "backend_control", "GET /api/v1/backend-control/status"),
                    self.evidence.ref("monitor", "bootstrap_control", "GET /api/v1/bootstrap-control/status"),
                ],
                metadata={
                    "status": backend_status.status,
                    "backend_port": str(backend_status.backend_port),
                    "control_port": str(backend_status.control_port),
                    "bootstrap_port": str(bootstrap_status.bootstrap_port),
                    "monitor_status": bootstrap_status.status,
                    "restart_endpoint": backend_status.restart_endpoint,
                    "monitor_restart_endpoint": bootstrap_status.restart_endpoint,
                },
                safe_actions=[self.actions.refresh("dashboard"), self.actions.restart_backend(), self.actions.restart_monitor_via_bootstrap()],
            ),
            self.cards.card(
                card_id="dashboard_project_profiles",
                screen="dashboard",
                card_type="project_profiles_status",
                title="Project Profiles",
                status="healthy",
                severity="success",
                happening="Perfis de projeto estao disponiveis como contexto governado para agentes e ferramentas.",
                why="Profiles informam workspaces, comandos e validacoes, mas nao concedem permissao por conta propria.",
                safety="safe",
                safety_reason="Endpoint read-only; permissions continuam no Workspace/Policy/Capability.",
                actions=["Abrir seletor de projetos.", "Atualizar profiles.", "Copiar resumo sanitizado."],
                evidence=[self.evidence.ref("monitor", "project_profiles", "GET /api/v1/mobile/view-model/projects")],
                metadata=ProjectProfileRegistryService().status(),
                safe_actions=[self.actions.refresh("dashboard"), self.actions.navigate("open_project_profiles", "Abrir projetos", "/api/v1/mobile/view-model/projects")],
            ),
            self.cards.card(
                card_id="dashboard_internal_skills",
                screen="dashboard",
                card_type="internal_skills_status",
                title="Skills Internas",
                status="healthy",
                severity="success",
                happening="Registry de skills governadas esta disponivel para agentes e UI.",
                why="Skills declaram capabilities, ferramentas permitidas, policies e validacoes; efeitos passam pelo Tool Gateway.",
                safety="safe",
                safety_reason="Endpoint read-only; execucao continua governada por policy/capability/approval.",
                actions=["Abrir Skills.", "Atualizar registry.", "Copiar resumo sanitizado."],
                evidence=[self.evidence.ref("monitor", "skills", "GET /api/v1/mobile/view-model/skills")],
                metadata=SkillManifestRegistryService().status().model_dump(),
                safe_actions=[self.actions.refresh("dashboard"), self.actions.navigate("open_skills", "Abrir Skills", "/api/v1/mobile/view-model/skills")],
            ),
            self.cards.card(
                card_id="dashboard_governed_sandbox",
                screen="dashboard",
                card_type="sandbox_status",
                title="Sandbox Governado",
                status="healthy" if SandboxWorkspaceService().status().status == "ok" else "degraded",
                severity="success" if SandboxWorkspaceService().status().status == "ok" else "warning",
                happening="Sandbox local disponivel para leitura, escrita, shell seguro e artifacts dentro da caixinha de areia.",
                why="O sandbox usa root proprio, policy de escape e trace por task; fora dele continuam valendo os gates fortes.",
                safety="safe",
                safety_reason="As operacoes com efeito ficam confinadas em C:\\Dev\\AIpinho\\sandboxes ou no root injetado por teste.",
                actions=["Abrir Sandbox.", "Criar task sandbox.", "Copiar resumo sanitizado."],
                evidence=[self.evidence.ref("monitor", "sandbox_status", "GET /api/v1/sandbox/status")],
                metadata=SandboxWorkspaceService().status().model_dump(),
                safe_actions=[self.actions.refresh("dashboard"), self.actions.navigate("open_sandbox", "Abrir Sandbox", "/api/v1/mobile/view-model/sandbox")],
            ),
            self.cards.card(
                card_id="dashboard_core_backend",
                screen="dashboard",
                card_type="service_status",
                title="Core Backend",
                status="healthy",
                severity="success",
                happening="Core Backend esta online para o contrato /api/v1.",
                why="O health/status fazem parte da fonte oficial do backend.",
                safety="safe",
                safety_reason="Leitura de status e read-only.",
                actions=["Atualizar status.", "Abrir Debugger.", "Copiar resumo sanitizado."],
                evidence=[self.evidence.ref("monitor", "health", "GET /api/v1/health")],
                metadata={"endpoint": "/api/v1/health"},
                safe_actions=[self.actions.refresh("dashboard"), self.actions.navigate("open_debugger", "Abrir Debugger", "/api/v1/mobile/view-model/debugger")],
            ),
            self.cards.card(
                card_id="dashboard_realtime",
                screen="dashboard",
                card_type="realtime_status",
                title="Realtime/SSE",
                status="healthy" if realtime_is_ok else "degraded",
                severity="success" if realtime_is_ok else "warning",
                happening="Realtime/SSE esta disponivel para sincronizacao incremental." if realtime_is_ok else "Realtime/SSE respondeu com estado degradado.",
                why="O mobile usa esse status como observabilidade; o estado final continua vindo do backend.",
                safety="safe" if realtime_is_ok else "caution",
                safety_reason="Heartbeat e eventos sao leitura/sincronizacao; falhas viram cautela, nao sucesso falso.",
                actions=["Atualizar heartbeat.", "Copiar resumo.", "Abrir eventos relacionados."],
                evidence=[self.evidence.ref("event", "realtime_status", "GET /api/v1/realtime/status")],
                metadata={
                    "endpoint": "/api/v1/realtime/status",
                    "mode": str(realtime_status.get("mode", "")),
                    "support_sse": str(realtime_status.get("support_sse", "")),
                    "port": str(realtime_status.get("port", "")),
                },
                safe_actions=[self.actions.refresh("dashboard")],
            ),
        ]
        try:
            multi_agent = MultiAgentObservabilityService().dashboard()
            for card in multi_agent.cards:
                status = "healthy" if card.status in {"ok", "online", "healthy", "idle"} else card.status
                severity = {
                    "success": "success",
                    "info": "info",
                    "warning": "warning",
                    "danger": "danger",
                    "error": "danger",
                    "blocked": "blocked",
                }.get(card.severity, "info")
                cards.append(
                    self.cards.card(
                        card_id=f"dashboard_{card.card_id}",
                        screen="dashboard",
                        card_type="multi_agent_observability",
                        title=card.title,
                        status=status,
                        severity=severity,
                        happening=card.summary,
                        why="Este card vem de /api/v1/dashboard/multi-agent e reflete stores reais de agentes, runs, delegacoes, ferramentas e policy.",
                        safety="safe" if severity in {"success", "info"} else "caution",
                        safety_reason="Leitura de observabilidade multiagente; a UI nao decide policy.",
                        actions=["Atualizar dashboard.", "Abrir Debugger 2.0.", "Copiar resumo sanitizado."],
                        evidence=[self.evidence.ref("monitor", card.card_id, "/api/v1/dashboard/multi-agent")],
                        metadata={"status": card.status, "severity": card.severity, "count": card.count if card.count is not None else ""},
                        safe_actions=[self.actions.refresh("dashboard")],
                    )
                )
        except Exception as exc:
            cards.append(
                self.cards.card(
                    card_id="dashboard_multi_agent_unavailable",
                    screen="dashboard",
                    card_type="multi_agent_observability",
                    title="Multi-Agent Dashboard",
                    status="degraded",
                    severity="warning",
                    happening=f"Observabilidade multiagente indisponivel: {exc.__class__.__name__}.",
                    why="O backend nao conseguiu montar o agregado multiagente; o detalhe tecnico fica no Debugger.",
                    safety="caution",
                    safety_reason="Falha de observabilidade nao deve ser mascarada como sucesso.",
                    actions=["Atualizar dashboard.", "Abrir Debugger 2.0."],
                    evidence=[],
                    metadata={"error": exc.__class__.__name__},
                    safe_actions=[self.actions.refresh("dashboard")],
                )
            )
        for port in (9088, 9089, 9098, 9099):
            enabled = port != 9099
            cards.append(
                self.cards.card(
                    card_id=f"dashboard_port_{port}",
                    screen="dashboard",
                    card_type="port_restart_policy",
                    title=f"Porta {port}",
                    status="healthy" if enabled else "blocked",
                    severity="info" if enabled else "blocked",
                    happening=f"Restart da porta {port} {'esta liberado pela policy' if enabled else 'esta bloqueado pela policy'}.",
                    why="O backend aggregator le a mobile_safe_action_policy e gera a acao segura.",
                    safety="caution" if enabled else "blocked",
                    safety_reason="Restart e side effect e exige confirmacao." if enabled else "9099 e porta de monitor/supervisao e so reinicia pelo bootstrap 9080.",
                    actions=["Reiniciar com confirmacao.", "Copiar policy sanitizada."] if enabled else ["Abrir Config.", "Copiar motivo do bloqueio."],
                    evidence=[self.evidence.ref("policy_decision", f"restart:{port}", f"restart policy {port}")],
                    metadata={"port": port, "side_effect": True},
                    safe_actions=[self.actions.restart_monitor_via_bootstrap()] if port == 9099 else [self.actions.restart_port(port)],
                )
            )
        cards.extend(
            [
                self.cards.card(
                    card_id="dashboard_legacy_rag",
                    screen="dashboard",
                    card_type="rag_legacy_warning",
                    title="Legacy RAG",
                    status="historical",
                    severity="info",
                    happening="Legacy RAG existe como referencia historica/diagnostica.",
                    why="Sprint 43 marcou legacy como current_truth_allowed=false.",
                    safety="caution",
                    safety_reason="Conteudo legado nao deve ser tratado como fonte de verdade atual.",
                    actions=["Abrir evidencia RAG.", "Copiar resumo sanitizado."],
                    evidence=[self.evidence.ref("rag_citation", "legacy_pinhoabacaxi_curated", "legacy curated namespace")],
                    metadata={"allowed_use": "historical_diagnostic_only", "current_truth_allowed": False},
                ),
                self.cards.card(
                    card_id="dashboard_maintenance",
                    screen="dashboard",
                    card_type="maintenance_status",
                    title="Maintenance/Regression",
                    status="healthy" if maintenance_is_ok else "degraded",
                    severity="info" if maintenance_is_ok else "warning",
                    happening="Maintenance, replay e regression estao disponiveis como diagnostico." if maintenance_is_ok else "Maintenance respondeu com avisos; verifique detalhes no Debugger.",
                    why="Esses modulos explicam invariants, diffs e failures sem aplicar reparo sozinho.",
                    safety="safe" if maintenance_is_ok else "caution",
                    safety_reason="Modo observabilidade/read-only no mobile; reparos continuam preview/approval/validation.",
                    actions=["Abrir Debugger.", "Criar support bundle preview."],
                    evidence=[self.evidence.ref("maintenance_run", "status", "GET /api/v1/maintenance/status")],
                    metadata={
                        "repair": "preview_only",
                        "invariant_count": maintenance_status.invariant_count,
                        "warnings": ", ".join(maintenance_status.warnings),
                    },
                    safe_actions=[self.actions.support_bundle_preview()],
                ),
            ]
        )
        critical_states = {"offline", "failed"}
        screen_status = "degraded" if any(card.status in critical_states or card.severity == "danger" for card in cards) else "healthy"
        warnings = [
            f"{card.title}: {card.status}"
            for card in cards
            if card.status != "historical" and (card.status in {"degraded", "unknown"} or card.severity == "warning")
        ]
        return MobileDashboardViewModel(
            state=MobileScreenState(
                screen="dashboard",
                status=screen_status,
                human_summary="Dashboard humano carregado com status, ports, RAG legado e diagnostico avancado.",
                warnings=warnings,
            ),
            cards=cards,
            trace_id="mobile_vm_dashboard",
        )
