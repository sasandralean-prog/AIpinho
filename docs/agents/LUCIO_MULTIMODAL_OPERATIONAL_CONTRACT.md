# Lúcio Multimodal Operational Contract

## Inputs

- `text`
- `artifact_refs`
- `screenshot_refs`
- `image_refs`
- `file_refs`
- `session_id`
- `agent_id=lucio`

## Outputs

- `LucioMultimodalMessage`
- `LucioRouteDecision`
- `LucioAgentResponse`
- events `lucio_multimodal_message_created` e `lucio_visual_analysis_available`

## Rotas

- `answer_directly`
- `ask_clarification`
- `delegate_to_codex`
- `delegate_to_aipinho`
- `create_plan_only`
- `block`
- `request_better_image`
- `request_missing_artifact`

## Side Effects

Lúcio não aplica patch, não executa shell e não grava arquivos locais diretamente. A execução deve ser delegada para agentes executores governados, com policy, approval e validation quando aplicável.

