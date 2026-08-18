# Knowledge Base Update

## Pattern

PUBLIC_RUNTIME_EXECUTION_GAP

## Category

- Lifecycle Regression
- TaskRun Regression
- Artifact Regression
- Validation Regression
- Completion Regression
- Speaker Truth Regression

## Generic Root Cause

A public integration layer can validate Gateway/Kernel readiness while failing to dispatch executable contracts into the canonical runtime path.

## Reusable Detection

Flag a regression when an executable public contract has any of:

- requires_task=true
- execution_required=true
- artifact_generation=true
- validation_required=true
- non-empty expected_outputs

and the response lacks:

- task_run_id
- timeline
- artifacts
- validation
- completion
- Speaker Truth

## Generic Remediation

Route public executable contracts through a contract-driven execution bridge or return structured blocked status when no canonical runtime route exists.

Do not add project-specific, provider-specific, or Fire Test-specific rules.
