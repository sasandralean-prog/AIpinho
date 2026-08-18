# Self-Healing Detectors

Detectores implementados inicialmente:

- `state_consistency`
- `dashboard_debugger_consistency`

O detector `state_consistency` converte issues de `StateConsistencyReport` em candidatos.

O detector `dashboard_debugger_consistency` procura divergencias entre dashboard e debugger.

Detectores planejados:

- stale run;
- pending approval stale;
- orphan artifact;
- missing validation;
- completed without evidence;
- delegation consistency;
- tool invocation consistency;
- event sequence;
- view-model divergence;
- memory contradiction;
- provider misconfigured;
- security leak;
- report missing.

Cada detector deve produzir candidatos generalistas, sem depender de sprint, prompt, usuario, path ou projeto especifico.
