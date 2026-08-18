from __future__ import annotations
from aipinho.schemas.ux.ux_error_message import UXErrorMessage
class UXErrorMessageService:
    DEFAULTS={"backend_down":"Backend principal indisponivel. Algumas acoes estao bloqueadas.","realtime_down":"Sincronizacao em tempo real indisponivel. Usando atualizacao periodica.","artifact_service_down":"Servico de arquivos indisponivel. Uploads e downloads podem falhar.","monitor_down":"Monitor indisponivel. Reinicio de servicos nao esta disponivel pela API.","event_registry_down":"Registro de eventos indisponivel. Eventos desconhecidos nao serao interpretados.","context_kernel_down":"Context Kernel indisponivel. Pre-visualizacao de contexto esta desativada.","token_redacted":"Conteudo sensivel foi redigido antes da exibicao."}
    def message(self, code: str, severity: str="warning", next_safe_action: str|None="retry") -> UXErrorMessage:
        return UXErrorMessage(code=code,severity=severity,human_message=self.DEFAULTS.get(code,"Operacao indisponivel no momento."),recoverable=severity!="critical",next_safe_action=next_safe_action)
