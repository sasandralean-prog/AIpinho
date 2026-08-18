# Known Issues

## KI-001 - Visual QA Not Rerun During RC1 Hardening

- Severity: low.
- Affected component: Mobile and Launcher UX.
- Description: Backend and contract validations passed. Sprint 16 captured a physical-device mobile dashboard smoke showing backend online, but full visual QA across all mobile and launcher tabs was not completed.
- Workaround: Run mobile/launcher smoke manually before using RC1 for a long supervised session.
- Recommended fix: Add automated visual assertions for key screens in a future sprint.
- Suggested sprint: RC2 visual hardening.
- Status: open.

## KI-002 - Regression Suite Is Initial

- Severity: medium.
- Affected component: Multi-agent regression coverage.
- Description: The new suite validates representative contracts but is not yet exhaustive for every route and UI surface.
- Workaround: Add a regression whenever a production bug is found.
- Recommended fix: Expand the matrices into dedicated tests gradually.
- Suggested sprint: continuous hardening.
- Status: open.

## KI-003 - Self-Healing Detector Set Is Conservative

- Severity: low.
- Affected component: Governed Self-Healing.
- Description: Initial detectors focus on state and dashboard/debugger consistency.
- Workaround: Use debugger reports for deeper root-cause analysis.
- Recommended fix: Add specialized detectors for provider, artifact and UI divergence.
- Suggested sprint: future observability hardening.
- Status: open.

## KI-004 - Chat Principal Ainda Nao Encaminha Escrita Governada Simples

- Severity: high.
- Affected component: Chat operation routing and write execution bridge.
- Description: The multi-agent Tool Gateway can create files in target_mutable workspaces, but a direct prompt in the main AIpinho chat asking for a safe file write may be routed as governed_project_rebuild and blocked with workspace_missing instead of becoming an explicit create_file/write contract.
- Workaround: Fixed in RC2 for explicit create-file prompts; use target_mutable workspace context or provide a path.
- Recommended fix: Implemented `governed_file_write` and `GovernedWriteRequest` bridge to Tool Gateway.
- Suggested sprint: RC2 write-flow unification.
- Status: fixed_rc2.

## KI-005 - Runtime State Can Pollute Dashboard After Field Trials

- Severity: medium.
- Affected component: Multi-agent dashboard and runtime stores.
- Description: Old sessions/runs/delegations/approvals can leave dashboard agents in blocked/degraded state even when backend health is online. Sprint 16 required a conservative cleanup backup and reset before clean field evidence.
- Workaround: Use `/api/v1/runtime/hygiene/preview` and `/api/v1/runtime/hygiene/apply/{preview_id}` before a formal field trial.
- Recommended fix: Implemented conservative preview/apply hygiene; evidence is not deleted.
- Suggested sprint: RC2 state hygiene.
- Status: fixed_rc2.

## KI-006 - Historical Tool Block Overrode Completed Run State

- Severity: high.
- Affected component: Agent session status and mobile agent view-model.
- Description: During Sprint 20, an expected source-readonly write denial remained in the event stream and made a completed, validated run appear blocked in the mobile view-model.
- Workaround: None required after Sprint 20 fix.
- Recommended fix: Completed runs now prefer run-level terminal status instead of resolved historical tool-level blocks.
- Suggested sprint: Sprint 20 dogfood stabilization.
- Status: fixed_sprint20.
# Sprint 22: Limitação Multimodal Conhecida

O pipeline multimodal atual usa intake governado, metadados sanitizados e análise visual contratual. Inspeção profunda de pixels depende do provider multimodal configurado e saudável. Quando esse provider não estiver disponível, Lúcio deve responder com limitação explícita, pedir melhor evidência ou delegar para Codex/AIpinho com artifact refs.
# Sprint 26 Sandbox

- A dedicated interactive Launcher/Mobile sandbox screen is pending; backend endpoints, mobile view-model and dashboard card are available.
- Symlink containment is enforced for existing paths. Platform-specific junction edge cases should remain in the security regression backlog.
- Shell classification is deliberately conservative; unclassified commands are blocked instead of guessed.

# Sprint 27 Project Factory

- Android Kotlin sandbox projects are structurally validated. Full Android build is reported as a warning when Android SDK/Gradle availability is not guaranteed inside the sandbox runtime.
- The first live smoke found and fixed a generic name-extraction bug where a technical descriptor could be mistaken for the project name before explicit `chamado/nomeado/named/called` markers were prioritized.
