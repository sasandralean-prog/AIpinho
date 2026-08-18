# Multi-Agent Tool Gateway

## Objetivo

O Tool Gateway e a camada unica por onde AIpinho, Lucio, Codex e Gemini solicitam acoes operacionais. Agentes solicitam; o gateway normaliza, avalia policy/capability/workspace, executa quando permitido, emite eventos e devolve resultado sanitizado.

## Fluxo canonico

AgentRun -> ToolInvocation -> WorkspaceResolver -> PolicyDecisionService -> execucao controlada -> AgentEvent -> Artifact/Evidence/Validation -> Timeline.

## Contratos

ToolDefinition descreve capability, risco, necessidade de workspace, approval, autoapproval, eventos, artifacts e permissoes de filesystem/shell.

ToolInvocation registra agent_id, session_id, run_id, ferramenta, capability, operation_type, workspace_role, policy_decision_id, approval/auto_approval, status, evidencias, artifacts e raw_ref opcional.

## Policy hook

PolicyDecisionService.evaluate_tool_invocation recebe agente, sessao, run, ferramenta, capability, workspace, risco e input sanitizado. A decisao pode ser allow, deny, require_approval ou auto_approve.

O modo atual segue liberdade operacional governada: leitura, artifact, validacao, report, patch preview, escrita em workspace mutavel e shell readonly/test/build/package podem ser autoaprovados por config. Source_readonly, forbidden/protected, shell destrutivo, network, git write, process control e unknown shell sao bloqueados por padrao.

## Workspace hook

WorkspaceResolver usa registry config-driven com longest-path match, deny-overrides, protecao contra traversal e roles:

- source_readonly
- target_mutable
- system_mutable
- protected
- forbidden
- unknown

source_readonly nunca permite write. protected/forbidden bloqueiam.

## Shell governance

run_shell exige categoria. Categorias perigosas sao bloqueadas por padrao. stdout/stderr sao sanitizados e entram como eventos escondidos no modo normal.

## Artifacts

Artifacts criados pelo gateway possuem artifact_id, filename, content_type, size, origin, source operation e endpoint de download sem token. O token deve ir no header Authorization.

## Validation hook

validate padroniza ValidationResult e ValidationStep. Operacoes com side effect podem retornar validacao minima e eventos associados.

## Normal/details/raw

Timeline normal mostra eventos humanos e sanitizados. Details inclui eventos tecnicos. Raw permanece oculto por padrao.

## Limitacoes atuais

- Approval real ainda e tratado como policy result/metadata no gateway multi-agent; integracao profunda com o ApprovalService existente fica para sprint posterior.
- Patch apply esta como hook contratual minimo, sem substituir o pipeline de patch completo.
- Shell real existe, mas testes usam runner fake.

## Proximos passos

Sprint 4 deve conectar approvals reais, patch pipeline completo e UI dedicada para invocacoes por agente sem duplicar fluxos existentes.
