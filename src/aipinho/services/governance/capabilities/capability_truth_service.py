from __future__ import annotations

from aipinho.schemas.governance.capability_truth import CapabilityAnswerPolicy, CapabilityTruthSnapshot
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class CapabilityTruthService:
    """Answers operational capability questions from canonical runtime truth."""

    def snapshot(self) -> CapabilityTruthSnapshot:
        try:
            runtime = TaskRuntimeService().status()
            write_enabled = bool(runtime.write_enabled)
            shell_enabled = bool(runtime.shell_enabled)
            enabled = bool(runtime.enabled)
        except Exception:
            write_enabled = False
            shell_enabled = False
            enabled = True
        limitations = [
            "Escrita, shell, build e patch dependem de workspace, policy, plano executavel e approval quando exigido.",
            "Nao executo side effects fora do fluxo governado.",
        ]
        return CapabilityTruthSnapshot(
            can_execute_governed_tasks=enabled,
            can_write_workspace_when_allowed=write_enabled,
            can_run_shell_when_allowed=shell_enabled,
            limitations=limitations,
        )

    def answer(self) -> tuple[str, dict[str, object]]:
        snapshot = self.snapshot()
        policy = CapabilityAnswerPolicy()
        write_text = "posso criar/modificar arquivos quando o workspace e a policy permitirem" if snapshot.can_write_workspace_when_allowed else "escrita pode estar desabilitada no runtime atual"
        shell_text = "posso solicitar shell/build governado quando permitido" if snapshot.can_run_shell_when_allowed else "shell/build pode estar desabilitado no runtime atual"
        message = (
            "CAPABILITY_TRUTH_READY\n"
            "Tenho capacidade de operar tarefas governadas: posso criar preview, pedir approval e executar acoes permitidas pela policy. "
            f"Para arquivos, {write_text}. Para comandos, {shell_text}. "
            "Nao declaro execucao real sem approval quando exigido, runtime, expected outputs e validacao."
        )
        return message, {"capability_truth": snapshot.model_dump(), "answer_policy": policy.model_dump()}
