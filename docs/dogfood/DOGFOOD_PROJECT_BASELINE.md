# Dogfood Project Baseline

## Fixture

Root:

`C:\Dev\AIpinho\field_trials\dogfood_sprint20`

Source-readonly project:

`C:\Dev\AIpinho\field_trials\dogfood_sprint20\source_readonly_project`

Target-mutable project:

`C:\Dev\AIpinho\field_trials\dogfood_sprint20\target_mutable_project`

## Known Source Issue

The source fixture contains a small Python module where `average([])` raises `ZeroDivisionError`.

Expected target behavior:

- `average([])` returns `0.0`;
- non-empty averages keep normal behavior;
- existing `total()` behavior remains unchanged.

## Source Safety Evidence

- Source hash before: `5be183b59d6e3c652a61d96b23d82cc027abe46c996da48e2f4b284c790fc655`
- Source hash after: `5be183b59d6e3c652a61d96b23d82cc027abe46c996da48e2f4b284c790fc655`
- Source unchanged: yes.

## Policy Baseline

- Reading source-readonly is allowed.
- Writing source-readonly is denied.
- Writing target-mutable can be autoapproved in governed autorun when policy allows it.
- Test shell in target-mutable can be autoapproved when categorized as `test_shell`.

