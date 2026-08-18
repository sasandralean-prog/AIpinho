# Sprint L — Operator Experience + Speaker Truth Enforcement

## Veredito

OPERATOR_EXPERIENCE_SPEAKER_TRUTH_READY

## Implementado

- Speaker Truth Auditor para outputs externos de operadores.
- Gemini/Codex externos passam a emitir sinais de auditoria, nao resposta final substituta.
- Review loop acionado quando output externo tenta reescrever, resumir, completar ou melhorar a resposta da AIpinho.
- Universal Task Session limitada aos estados publicos permitidos: CREATED, QUEUED, RUNNING, WAITING_APPROVAL, WAITING_USER, COMPLETED, FAILED, CANCELLED e TIMEOUT.
- Launcher com toolbar de operador, busca, copia, exportacao, expandir conversa, scroll interno e aviso de nova mensagem sem auto-scroll invasivo.
- Mobile com toolbar compartilhada nos agentes, texto selecionavel, copia de mensagem/conversa, exportacao, expandir, busca, scroll interno e aviso de nova mensagem.

## Arquivos alterados

- src/aipinho/services/external_speaker_truth_auditor.py
- src/aipinho/services/external_adapter_registry.py
- src/aipinho/services/external_collaboration_service.py
- src/aipinho/schemas/runtime/universal_task_session.py
- src/aipinho/services/runtime/universal_task_session_service.py
- apps/launcher/ui/tabs/agent_desktop_tab.py
- apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/AgentTabScreen.kt
- tests/unit/test_universal_task_session_service.py
- tests/unit/test_continuous_collaboration_runtime.py
- tests/unit/test_external_collaboration_layer.py
- tests/integration/test_launcher_multi_agent_ui_contract.py
- apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/ExecutorMessageCopyContractTest.kt

## Testes executados

- python -m py_compile nos modulos Python alterados.
- python -m pytest tests/unit/test_universal_task_session_service.py tests/unit/test_continuous_collaboration_runtime.py tests/unit/test_external_collaboration_layer.py tests/integration/test_launcher_multi_agent_ui_contract.py -q
- .\gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.ExecutorMessageCopyContractTest --tests br.com.aipinho.mobile.MultiAgentMobileUiContractTest --tests br.com.aipinho.mobile.Sprint19MobileUxContractTest
- .\gradlew.bat :app:assembleDebug

## Resultados

- Python focado: 25 passed.
- Android unit focado: BUILD SUCCESSFUL.
- Android assembleDebug: BUILD SUCCESSFUL.
- APK instalado no dispositivo fisico ZF5253V88S.
- Launcher recompilado e copiado para C:\Users\rafae\Desktop\AIpinhoLauncher.exe.

## Evidencias

- APK: C:\Dev\AIpinho\apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk
- Launcher: C:\Dev\AIpinho\dist\AIpinhoLauncher.exe
- Launcher desktop: C:\Users\rafae\Desktop\AIpinhoLauncher.exe

## Riscos restantes

- QA visual manual ainda e recomendado para confirmar ergonomia fina do scroll em telas pequenas.
- A camada de auditoria bloqueia reescrita externa por padroes textuais; futuros providers podem exigir ampliacao configuravel dos sinais.
