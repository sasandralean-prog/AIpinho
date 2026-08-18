# Trace Graph Model

O trace graph conecta entidades operacionais em um grafo auditavel.

No Sprint 12, `GET /api/v1/debugger/traces/{run_id}` retorna `trace_graph` para runs do kernel multiagente.

Nos do grafo:

- session;
- run;
- parent_run;
- delegation;
- event;
- tool_invocation;
- policy_decision;
- approval;
- validation;
- artifact.

Arestas principais:

- `owns`;
- `parent_of`;
- `created_child_run`;
- `emits`;
- `references`;
- `uses_tool`;
- `checked_by`.

O grafo e somente leitura. Ele nao corrige, aprova, aplica patch ou executa shell.
