# Desktop Multi-Agent Launcher

The Launcher operational order is:

1. Dashboard
2. AIpinho
3. Lucio
4. Codex
5. Gemini
6. Pipeline
7. Debugger 2.0
8. Artifacts
9. Configuracoes

Lucio, Codex and Gemini use one shared `AgentDesktopTab` implementation backed
by a centralized endpoint catalog. This removes duplicated session, timeline,
polling and dialog behavior while preserving provider-specific routes and
payloads.

The AIpinho chat keeps its specialized human presentation mapper.

