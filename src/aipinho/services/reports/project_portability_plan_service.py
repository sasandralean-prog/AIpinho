from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.project_tree_service import ProjectTreeService
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectPortabilityPlanService:
    def __init__(
        self,
        tree_service: ProjectTreeService | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.tree_service = tree_service or ProjectTreeService()
        self.config = config or load_yaml_file(
            PATHS.config_root / "reports" / "portability_plan_policy.yaml",
            critical=True,
            root=PATHS.config_root / "reports",
        )

    def build(
        self,
        *,
        analysis,
        recommendations,
        workspace_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_status = self._target_status(workspace_references)
        stages = [
            {
                "stage_id": str(item.get("stage_id")),
                "title": str(item.get("title")),
                "objective": str(item.get("objective")),
                "validation": list(item.get("validation", []) or []),
            }
            for item in self.config.get("stages", [])
            if isinstance(item, dict)
        ]
        first = self._first_sprint(target_status)
        risks = [
            {
                "risk": "evidence_scope",
                "summary": "O plano deve ser revisto se arquivos relevantes ficaram fora do contexto analisado.",
            },
            {
                "risk": "behavioral_parity",
                "summary": "A portabilidade pode perder comportamento se os fluxos observados nao forem convertidos em testes.",
            },
            {
                "risk": "target_drift",
                "summary": "O workspace alvo pode mudar entre o planejamento e a execucao; um novo snapshot deve preceder escrita.",
            },
        ]
        return {
            "target_status": target_status,
            "macro_plan": stages,
            "first_sprint": first,
            "risks": risks,
            "permissions": [
                "Leitura do source durante analise.",
                "Leitura do target antes de cada sprint.",
                "Escrita no target somente por preview, approval e validation.",
                "Nenhuma escrita no source.",
            ],
            "next_steps": [
                "Revisar este plano contra as evidencias citadas.",
                "Confirmar o escopo pequeno do primeiro sprint.",
                "Gerar preview governado antes de qualquer escrita.",
                "Executar validacoes previstas e comparar source/target sem copiar cegamente.",
            ],
            "validation_strategy": list(
                self.config.get("validation_strategy", []) or []
            ),
            "recommendation_count": len(recommendations),
            "observed_structures": list(getattr(analysis, "structures", [])),
        }

    def _target_status(
        self,
        workspace_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target = next(
            (
                item
                for item in workspace_references
                if str(item.get("role")) == "target_mutable" and item.get("path")
            ),
            None,
        )
        if target is None:
            return {
                "status": "not_declared",
                "path": None,
                "files_seen": None,
                "dirs_seen": None,
            }
        tree = self.tree_service.build_tree_summary(
            ProjectAnalysisRequest(
                workspace=str(target["path"]),
                goal="codebase_overview",
                max_files=1,
            )
        )
        return {
            "status": tree.status,
            "path": str(target["path"]),
            "files_seen": tree.total_files_seen,
            "dirs_seen": tree.total_dirs_seen,
            "top_level": list(tree.top_level[:20]),
            "warnings": list(tree.warnings),
            "violations": list(tree.violations),
        }

    def _first_sprint(self, target_status: dict[str, Any]) -> dict[str, Any]:
        empty = (
            target_status.get("status") == "ok"
            and target_status.get("files_seen") == 0
        )
        template_key = "empty_target" if empty else "existing_target"
        raw = self.config.get("first_sprint", {}).get(template_key, {})
        return raw if isinstance(raw, dict) else {}
