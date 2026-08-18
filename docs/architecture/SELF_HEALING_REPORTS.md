# Self-Healing Reports

Relatorios de self-healing sao artifacts sanitizados.

Tipos:

- relatorio diagnostico por candidato;
- export geral de candidatos/runs/status;
- evidencia para supervisor humano.

Garantias:

- raw escondido por padrao;
- secrets redigidos;
- download protegido por token;
- relatorio nao substitui validacao operacional;
- falhas continuam visiveis no dashboard/debugger.

Endpoint:

- `POST /api/v1/self-healing/export-report`
