# Validation Authority

Execution environment determines what claims it can prove.

## Proof Classes

- `static_repository` - repository files, links, schemas, scripts, or docs can
  be inspected without executing runtime.
- `unit` - focused automated tests pass.
- `regression` - wider automated tests relevant to the boundary pass.
- `cloud_integration` - integration proof produced in a cloud environment.
- `local_integration` - integration proof produced against Rafa's local overlay.
- `diagnostic_public` - public/runtime path reached for diagnostic evidence.
- `final_public` - final public validation path completed at the claimed scope.

## Claim Rules

- Cloud agents may implement local-sensitive code, run deterministic tests, and
  push branches.
- Cloud agents may not claim local GGUF inference, Pinhoabacaxi integration,
  Windows-specific behavior, or FireTest local public validation unless that
  evidence was actually produced in that environment.
- Local agents may claim local proof only for capabilities actually present and
  exercised.
- A blocked result can be correct proof when it honestly preserves evidence,
  reason, terminality, and SpeakerTruth.

## Engineering Equivalent of SpeakerTruth

Final engineering summaries may only claim the proof observed. Do not convert a
unit test into public proof, or repository inspection into local runtime proof.
