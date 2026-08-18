# Sprint 4+5 - Launcher Agent Console + Ownership, Locks e Seguranca entre Ilhas

## Veredito
READY_WITH_WARNINGS

## Objetivo
Implementar console operacional desktop para as ilhas AIpinho, Lucio, Gemini e Codex, com Bridge Monitor, Artifact Center, Approval Center e monitoramento de locks, e adicionar camada backend de ownership/locks/conflict guard sem criar bypass de governanca.

## Implementado
- Endpoint leve `/api/v1/agent-bridge/status` sem diagnostico profundo automatico.
- Endpoints de bridge active/details/cancel para monitorar delegacoes.
- Endpoint de locks com listagem, consulta por workspace, release, override, write-conflict check e hop guard.
- Artifact provenance e revalidation em `/api/v1/artifacts/{artifact_id}/provenance` e `/api/v1/artifacts/{artifact_id}/revalidate`.
- Alias seguro `/api/v1/approvals/pending` e `/api/v1/approvals/{approval_id}/deny` para o centro de approvals.
- Launcher tab `Agentes` com Agent Console, Bridge Monitor, Artifact Center, Approval Center e Workspace Locks.
- Build do launcher desktop gerado em `C:\Dev\AIpinho\dist\AIpinhoLauncher.exe`.

## Arquivos criados
- `src/aipinho/schemas/agents/ownership.py`
- `src/aipinho/services/agents/workspace_lock_service.py`
- `src/aipinho/api/routers/agent_bridge_router.py`
- `src/aipinho/api/routers/workspace_lock_router.py`
- `apps/launcher/ui/api/agent_console_client.py`
- `apps/launcher/ui/tabs/agent_console_tab.py`
- `tests/integration/test_agent_bridge_sprint4_5_backend.py`
- `tests/integration/test_launcher_agent_console_contract.py`

## Arquivos alterados
- `src/aipinho/api/routers/__init__.py`
- `src/aipinho/api/routers/approval_router.py`
- `src/aipinho/api/routers/artifact_router.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `apps/launcher/ui/launcher_app.py`

## Contratos novos ou reforcados
- `GET /api/v1/agent-bridge/status`
- `GET /api/v1/agent-bridge/active`
- `GET /api/v1/agent-bridge/tasks/{bridge_task_id}/details`
- `POST /api/v1/agent-bridge/tasks/{bridge_task_id}/cancel`
- `GET /api/v1/locks`
- `POST /api/v1/locks`
- `GET /api/v1/locks/by-workspace`
- `POST /api/v1/locks/check-write`
- `POST /api/v1/locks/check-hop`
- `POST /api/v1/locks/{lock_id}/release`
- `POST /api/v1/locks/{lock_id}/override`
- `GET /api/v1/approvals/pending`
- `POST /api/v1/approvals/{approval_id}/deny`
- `GET /api/v1/artifacts/{artifact_id}/provenance`
- `POST /api/v1/artifacts/{artifact_id}/revalidate`

## Validacoes executadas
- `python -m py_compile` nos arquivos backend/launcher alterados: passed.
- `python -m pytest tests\integration\test_agent_bridge_sprint4_5_backend.py tests\integration\test_launcher_agent_console_contract.py tests\integration\test_universal_artifact_registry_api.py tests\integration\test_artifact_api.py tests\integration\test_agent_tool_gateway_api.py -q --durations=10`: 22 passed.
- `powershell -ExecutionPolicy Bypass -File scripts\package_launcher_desktop.ps1`: passed, exe gerado.

## Observacoes
- O status do Agent Bridge foi otimizado para nao chamar o dashboard profundo. O teste focado caiu para 0.27s.
- Override de lock existe como acao manual no Launcher e no backend, mas deve continuar sendo tratado como acao de alto risco pela UX/operacao.
- QA visual interativo do launcher nao foi executado nesta run; build e contrato de fonte foram validados.

## Riscos restantes
- Visual QA manual recomendado para densidade dos cards e fluxo de override/release.
- O diretorio `C:\Dev\AIpinho` nao respondeu como repositorio Git direto nesta sessao, entao nao houve diff via git.
