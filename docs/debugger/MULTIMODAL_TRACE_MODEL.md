# Multimodal Trace Model

## Eventos mínimos

- `lucio_multimodal_message_created`
- `lucio_visual_analysis_available`
- `lucio_multimodal_memory_write_skipped`
- `agent_artifact_uploaded`
- `agent_delegation_created`

## Campos recomendados

- `agent_id`
- `session_id`
- `operation_id`
- `artifact_refs`
- `route_type`
- `risk_level`
- `redaction_status`
- `evidence_refs`
- `delegated_to`

## Regras

Debugger pode mostrar metadados técnicos sanitizados. Chat normal não deve mostrar JSON bruto, raw bytes, tokens ou secrets.

