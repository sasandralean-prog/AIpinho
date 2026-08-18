# Governed Self-Healing

Self-Healing governado identifica inconsistencias operacionais e cria candidatos auditaveis.

Ele nao:

- apaga evidencia;
- mascara falhas;
- marca validacao como passada sem validacao;
- altera workspace sem policy;
- executa shell livre;
- bypassa approval.

Fluxo:

1. detector coleta sinais;
2. cria `SelfHealingCandidate`;
3. policy classifica risco;
4. baixo risco pode gerar artifact diagnostico ou reconstruir estado derivado;
5. medio/alto exige approval;
6. critico bloqueia para sprint manual;
7. apply gera `SelfHealingRun`;
8. validation registra resultado.

Endpoints principais:

- `GET /api/v1/self-healing/status`
- `POST /api/v1/self-healing/scan`
- `GET /api/v1/self-healing/candidates`
- `POST /api/v1/self-healing/candidates/{candidate_id}/apply`
- `POST /api/v1/self-healing/export-report`
