# Continue / VS Code Inspection Report

## Continue Extension
- Installed extension path: `C:\Users\rafae\.vscode\extensions\continue.continue-2.0.0-win32-x64`
- Version: `2.0.0`
- Extension manifest: `package.json`
- Activation: `onUri`, `onStartupFinished`, `onView:continueGUIView`

## Continue Config Schema
- Continue supports a workspace `config.json` with a `models` array.
- `ModelDescription` in `config_schema.json` includes `provider: "openai"`.
- OpenAI provider supports `apiBase`, `apiKey`, `model`, and standard completion options.
- The config schema also exposes `contextProviders`, `slashCommands`, `customCommands`, and `modelContextProtocolServers`.

## OpenAI-Compatible Integration
- A native Continue integration is feasible using `provider: "openai"` and `apiBase`.
- The schema indicates Continue can use a custom OpenAI-compatible endpoint for chat models.
- No explicit `GET /v1/models` or `POST /v1/chat/completions` implementation was found in the extension package source by string search.

## Chosen Integration Path
- Level 1: implement an OpenAI-compatible local endpoint in AIpinho at:
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- This enables Continue to connect as a local model provider using the OpenAI transport.

## Limitations and Risks
- The Continue extension package is compiled and does not expose a clear provider implementation in text search.
- The final integration must be tested in VS Code to verify the exact `config.json` shape and any additional required fields.
- Streaming is not implemented in the current AIpinho adapter and is marked as unsupported.

## Next Steps
1. Add the local OpenAI-compatible adapter to AIpinho.
2. Add Continue-specific integration docs and config examples.
3. Implement governance endpoints for preview/approval and action execution.
4. Validate with a live Continue session configured against `http://127.0.0.1:9088/v1`.
