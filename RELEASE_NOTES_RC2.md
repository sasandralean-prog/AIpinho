# AIpinho Multi-Agent RC2 Candidate

Date: 2026-06-13

## Summary

RC2 focuses on stabilization after RC1. The main AIpinho chat now routes explicit safe create-file prompts into the governed Tool Gateway instead of falling into project rebuild previews or generic workspace-missing blocks.

## Main Changes

- Added `governed_file_write` routing.
- Added `GovernedWriteRequest` as the normalized chat-to-tool write contract.
- Added `GovernedWriteChatService` to execute explicit chat writes through Tool Gateway, Policy Kernel, autoapproval/approval and validation.
- Added runtime hygiene preview/apply endpoints.
- Added health semantics endpoint separating backend, operational and observability states.
- Documented port 9099 as monitor/supervisor control plane.
- Sprint 20 dogfood validated governed project read/write/shell/validation/artifact flow on a controlled fixture.
- Governed shell now requires workspace context.
- Agent session status aggregation now keeps resolved tool-level blocks from overriding completed run state.

## Validation

- Focused RC2 regression: 37 passed.
- Python compile validation for changed files: passed.
- Sprint 20 dogfood focused validation: unit/session, tool gateway, golden paths and quick multi-agent regression passed.

## Known Limits

- Full mobile all-tabs visual QA remains recommended before long field trials.
- Full Launcher all-tabs visual smoke remains recommended before long field trials.
- Real provider smoke remains outside normal automated regression.
- RC3 supersedes RC2 for local daily-use packaging and operational readiness.

## Security Notes

- No evidence deletion in runtime hygiene.
- No direct write bypass from chat.
- source_readonly/protected/forbidden writes remain blocked.
- Raw remains hidden by default.
