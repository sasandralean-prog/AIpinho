# Self-Healing Policy

Regras de policy:

- risco baixo: pode aplicar apenas reparo reversivel ou artifact diagnostico;
- risco medio/alto: exige approval;
- risco critico: bloqueia para revisao manual;
- side effects fora de estado derivado/artifact exigem approval;
- validation e obrigatoria apos apply.

Permitido em baixo risco:

- gerar relatorio diagnostico;
- reconstruir view-model derivado;
- criar regression candidate;
- reconciliar estado derivado se a fonte primaria continuar intacta.

Proibido automaticamente:

- apagar arquivos;
- apagar eventos;
- editar workspace;
- executar shell;
- alterar policy;
- aprovar patch;
- marcar task como completa sem evidencia.
