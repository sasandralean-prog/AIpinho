# Golden Path Matrix

The golden path matrix lives at `tests/multi_agent/golden_path_matrix.yaml`.

It tracks the main usage paths that must stay valid:

- AIpinho simple chat.
- AIpinho readonly analysis.
- AIpinho target write with governed policy.
- Codex technical execution.
- Codex blocked source write.
- Gemini direct answer.
- Gemini to AIpinho delegation.
- Lucio direct multimodal analysis.
- Lucio to Codex delegation.
- Lucio to AIpinho delegation.
- Artifact upload/download.
- Dashboard visibility.
- Debugger trace graph.
- Low-risk self-healing.
- Validation failure truth.

The quick suite implements representative checks for these contracts and leaves the matrix as the expansion source for broader regression coverage.

