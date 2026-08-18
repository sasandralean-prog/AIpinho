# Operational Freedom Governance

## Filosofia

A AIpinho deve executar trabalho real. Policy nao e burocracia; e liberdade operacional com rastreabilidade.

Permitir por padrao quando:

- workspace e conhecido e permitido;
- acao e reversivel ou validavel;
- capability existe;
- risco e baixo ou medio;
- autoapproval policy permite;
- ha event trace e evidencia.

Interromper o usuario apenas quando houver risco real: destrutivo, irreversivel, secrets, exfiltracao, workspace protegido, shell perigoso, git write/push, process control amplo ou risco nao classificado.

## Default

`governed_autorun` e o default. Nesse modo, leitura, artifacts, validation, reports, escrita segura em `target_mutable` e shell readonly/test/build/package podem prosseguir automaticamente com eventos/audit.

## O que continua bloqueado

- source_readonly write;
- forbidden/protected workspace side effects;
- destructive shell;
- network shell;
- git write;
- process control;
- unknown shell;
- secrets/tokens no payload;
- critical risk.

## Transparencia

Toda decisao gera `policy_decision_id`. Toda autoaprovacao gera `auto_approval_id`. Todo bloqueio tem `reason_code`, `human_reason` e, quando possivel, `safe_alternative`.
