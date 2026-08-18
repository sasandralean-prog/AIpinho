# Multi-Agent Policy Kernel

## Objetivo

O Policy Kernel multiagente centraliza decisoes de allow, deny, require_approval e auto_approve para AIpinho, Lucio, Codex e Gemini. Ele nao existe para travar produtividade: existe para liberar trabalho real com rastreabilidade, workspace guard, reason codes, audit, autoapproval e alternativas seguras quando algo precisa ser bloqueado.

## Modos de execucao

- `safe_chat`: conversa/análise, sem side effects.
- `assisted_execution`: leitura/artifacts/validation autoaprovados; escrita e shell exigem aprovacao.
- `governed_autorun`: default. Leitura, escrita reversivel em `target_mutable`, artifacts, validation, report e shell readonly/test/build/package podem ser autoaprovados.
- `power_user`: mais liberdade em workspace autorizado, mantendo bloqueios de risco crítico.
- `unrestricted_local_lab`: reservado para laboratorio explicito, desabilitado por padrao.

## Contratos

`PolicyDecision` inclui agente, session, run, tool invocation, operation type, capability, workspace role, risk, execution mode, decision, reason_code, human_reason, safe_alternative, safe_actions e evidence_refs.

`AutoApprovalDecision` registra toda autoaprovacao com vinculo ao policy_decision_id.

## Perfis por agente

Os perfis ficam em `config/agents/agent_policy_profiles.yaml`.

- AIpinho e Codex: `governed_autorun`, execucao local habilitada, autoapproval para leitura/artifacts/target_write/shell seguro.
- Gemini e Lucio: podem usar gateway e delegar, mas escrita local direta fica desabilitada por perfil nesta fase.

## Workspace policy

Roles:

- `source_readonly`: leitura/search permitidos; escrita e patch apply negados.
- `target_mutable`: leitura/escrita/patch/shell seguro conforme modo.
- `system_mutable`: exige cuidado; autoapproval de escrita desabilitado por default.
- `protected`/`forbidden`: bloqueados por padrao.
- `unknown`: conservador.

## Risk policy

Low e medium podem ser autoaprovados em `governed_autorun` quando workspace/capability permitem. High exige aprovacao. Critical bloqueia.

## Event Bus

O Tool Gateway emite:

- `policy_check_started`
- `policy_check_completed`
- `policy_decision_allow`
- `policy_decision_deny`
- `policy_decision_require_approval`
- `policy_decision_auto_approve`
- `auto_approval_granted`
- `operation_blocked`
- `safe_alternative_available`

Esses eventos usam payload sanitizado e aparecem na timeline.

## Segurança

O kernel bloqueia source_readonly write, shell destrutivo, network shell, git write, process control, unknown shell, token em payload e risco crítico por padrao.
