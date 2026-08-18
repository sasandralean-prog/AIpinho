from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileDebuggerViewModel, MobileScreenState
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class DebuggerMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()
        self.actions = MobileSafeActionBuilder()

    def view_model(self, trace_id: str | None = None) -> MobileDebuggerViewModel:
        multi_agent_cards = []
        execution_graph_cards = []
        if trace_id and trace_id.startswith("task_run_"):
            try:
                graph = TaskRuntimeService().get_execution_graph(trace_id)
                if graph is not None:
                    execution_graph_cards.append(
                        self.cards.card(
                            card_id=f"debugger_execution_graph_{trace_id}",
                            screen="debugger",
                            card_type="execution_graph",
                            title="Execution Graph",
                            status=graph.status,
                            severity="warning" if graph.status in {"blocked", "failed"} else "info",
                            happening=f"DAG da task com {len(graph.nodes)} nos e {len(graph.edges)} dependencias.",
                            why="O runtime agora materializa dependencias, checkpoints e lifecycle em grafo auditavel.",
                            safety="safe" if graph.status not in {"blocked", "failed"} else "caution",
                            safety_reason="Card de debugger read-only; nao executa nem altera task.",
                            actions=["Abrir execution graph.", "Copiar resumo sanitizado."],
                            evidence=[self.evidence.ref("execution_graph", graph.graph_id, "task execution graph")],
                            metadata={
                                "run_id": trace_id,
                                "graph_id": graph.graph_id,
                                "nodes": len(graph.nodes),
                                "edges": len(graph.edges),
                                "ready_nodes": [node.node_id for node in graph.nodes if node.status == "ready"],
                            },
                            trace_id=trace_id,
                        )
                    )
            except Exception as exc:
                execution_graph_cards.append(
                    self.cards.card(
                        card_id=f"debugger_execution_graph_unavailable_{trace_id}",
                        screen="debugger",
                        card_type="execution_graph",
                        title="Execution Graph",
                        status="degraded",
                        severity="warning",
                        happening=f"Execution graph indisponivel: {exc.__class__.__name__}.",
                        why="Falha de observabilidade nao deve virar sucesso falso.",
                        safety="caution",
                        safety_reason="Sem graph, a UI mostra degradacao explicita.",
                        actions=["Atualizar Debugger."],
                        evidence=[],
                        metadata={"run_id": trace_id, "error": exc.__class__.__name__},
                    )
                )
        try:
            events = MultiAgentObservabilityService().debugger_events(run_id=trace_id if trace_id and trace_id.startswith("agent_run_") else None, limit=25, include_hidden=False)
            for event in events.events[:10]:
                status = {
                    "received": "running",
                    "created": "running",
                    "running": "running",
                    "succeeded": "completed",
                    "completed": "completed",
                    "blocked": "blocked",
                    "failed": "failed",
                }.get(event.status, "unknown")
                severity = {
                    "error": "danger",
                    "danger": "danger",
                    "blocked": "blocked",
                    "warning": "warning",
                    "success": "success",
                    "info": "info",
                }.get(event.severity, "info")
                multi_agent_cards.append(
                    self.cards.card(
                        card_id=f"debugger_multi_agent_{event.event_id}",
                        screen="debugger",
                        card_type="multi_agent_event",
                        title=event.event_type,
                        status=status,
                        severity=severity,
                        happening=event.human_message,
                        why=f"Evento sanitizado vindo de {event.source}; raw continua oculto por padrao.",
                        safety="blocked" if status == "blocked" else ("caution" if severity in {"warning", "danger"} else "safe"),
                        safety_reason="Debugger e leitura tecnica; nenhuma acao operacional e executada pela UI.",
                        actions=["Filtrar eventos.", "Copiar log sanitizado.", "Abrir entidade relacionada."],
                        evidence=[self.evidence.ref("event", event.event_id, event.event_type)],
                        metadata={"agent_id": event.agent_id or "", "run_id": event.run_id or "", "source": event.source},
                        trace_id=event.run_id,
                        event_ids=[event.event_id],
                    )
                )
        except Exception as exc:
            multi_agent_cards.append(
                self.cards.card(
                    card_id="debugger_multi_agent_unavailable",
                    screen="debugger",
                    card_type="multi_agent_event",
                    title="Debugger multiagente",
                    status="degraded",
                    severity="warning",
                    happening=f"Eventos multiagente indisponiveis: {exc.__class__.__name__}.",
                    why="A falha e mostrada como degradacao de observabilidade, nao como sucesso.",
                    safety="caution",
                    safety_reason="Sem eventos, a UI nao deve inventar estado.",
                    actions=["Atualizar Debugger."],
                    evidence=[],
                    metadata={"error": exc.__class__.__name__},
                )
            )
        cards = [
            self.cards.card(
                card_id="debugger_events",
                screen="debugger",
                card_type="events_debugger",
                title="Eventos Sanitizados",
                status="healthy",
                severity="info",
                happening="Debugger 2.0 mostra eventos filtrados, traces e raw sanitizado por referencia.",
                why="Eventos desconhecidos nao sao renderizados como normal.",
                safety="safe",
                safety_reason="Debugger mobile e read-only.",
                actions=["Filtrar eventos.", "Copiar log sanitizado.", "Abrir raw viewer se houver raw_ref."],
                evidence=[self.evidence.ref("event", "latest", "event stream")],
                raw_ref="raw_debugger_latest",
                trace_id=trace_id or "mobile_vm_debugger",
                safe_actions=[self.actions.open_trace(trace_id or "mobile_vm_debugger")],
            ),
            self.cards.card(
                card_id="debugger_invariant",
                screen="debugger",
                card_type="invariant_violation",
                title="Invariant Violation",
                status="unknown",
                severity="danger",
                happening="Invariant violations aparecem como diagnostico explicavel.",
                why="Maintenance verifica incoerencias sem aplicar reparo automatico.",
                safety="blocked",
                safety_reason="Quando invariant falha, o mobile bloqueia acao operacional e mostra evidencia.",
                actions=["Abrir trace.", "Gerar regression candidate.", "Copiar resumo."],
                evidence=[self.evidence.ref("maintenance_run", "latest", "maintenance invariant")],
                metadata={"repair": "preview_only"},
            ),
            self.cards.card(
                card_id="debugger_replay_regression",
                screen="debugger",
                card_type="replay_regression",
                title="Replay / Regression",
                status="unknown",
                severity="warning",
                happening="Replay/regression mostram divergencias e failures.",
                why="Comparacao ajuda a separar bug novo de regressao antiga.",
                safety="safe",
                safety_reason="Dry-run/read-only por contrato mobile.",
                actions=["Abrir diff.", "Copiar failure.", "Abrir report."],
                evidence=[self.evidence.ref("replay_run", "latest", "replay diff")],
                metadata={"dry_run": True},
            ),
            self.cards.card(
                card_id="debugger_eval_grounding",
                screen="debugger",
                card_type="eval_grounding",
                title="Evals Grounding/Citation/Safety",
                status="unknown",
                severity="info",
                happening="Evals explicam grounding, citation coverage e safety.",
                why="Resposta humana deve ser auditavel sem despejar raw.",
                safety="safe",
                safety_reason="Evals sao diagnostico read-only.",
                actions=["Abrir eval trace.", "Copiar relatorio sanitizado."],
                evidence=[self.evidence.ref("validation", "eval_latest", "eval report")],
                metadata={"raw_default_visible": False},
            ),
            self.cards.card(
                card_id="debugger_multimodal",
                screen="debugger",
                card_type="vision_ocr",
                title="Vision/OCR",
                status="unknown",
                severity="info",
                happening="Vision/OCR aparecem como evidencia multimodal com confidence e trace.",
                why="Imagem e OCR nao entram automaticamente no RAG sem preview.",
                safety="caution",
                safety_reason="Multimodal e evidencia; ingest exige policy/preview.",
                actions=["Abrir vision run.", "Copiar OCR sanitizado.", "Ver confidence."],
                evidence=[
                    self.evidence.ref("vision_run", "latest", "vision run"),
                    self.evidence.ref("ocr_run", "latest", "ocr run"),
                ],
                metadata={"vision_rag_auto_ingest": False},
            ),
        ]
        cards.extend(execution_graph_cards)
        cards.extend(multi_agent_cards)
        return MobileDebuggerViewModel(
            state=MobileScreenState(
                screen="debugger",
                status="healthy",
                human_summary="Debugger humano carregado com eventos, raw sanitizado, maintenance, replay, evals e multimodal.",
            ),
            cards=cards,
            trace_id=trace_id or "mobile_vm_debugger",
            filters=["events", "policy", "context", "rag", "memory", "skill", "maintenance", "model", "validation", "patch", "artifact", "supervisor", "speaker", "mobile_sync", "raw_sanitized"],
        )
