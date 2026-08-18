# Debugger 2.0 Multi-Agent

O Debugger 2.0 multiagente mostra eventos sanitizados, referencias e entidades operacionais do kernel multiagente.

Endpoints:

- `GET /api/v1/debugger/events`
- `GET /api/v1/debugger/traces/{run_id}`
- `GET /api/v1/debugger/entities/{entity_type}/{entity_id}`
- `POST /api/v1/debugger/export`
- `GET /api/v1/debugger/filters`

Filtros suportados:

- `agent_id`
- `session_id`
- `run_id`
- `delegation_id`
- `tool_invocation_id`
- `policy_decision_id`
- `approval_id`
- `artifact_id`
- `validation_id`
- `event_type`
- `status`
- `severity`
- `text`
- `cursor`
- `include_hidden`
- `mode`

O Debugger combina eventos de:

- agent event bus;
- policy audit;
- tool gateway;
- self-healing.

Raw tecnico continua escondido por padrao. O endpoint retorna apenas payload sanitizado.
