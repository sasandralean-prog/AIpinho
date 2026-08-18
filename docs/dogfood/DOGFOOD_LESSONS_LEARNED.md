# Dogfood Lessons Learned

## Runtime State Must Distinguish Evidence From Final Status

A blocked tool can be a successful safety proof when the final run is completed and validation passed. Aggregators must avoid collapsing historical safety evidence into final task failure.

## Shell Requires Workspace Context

Governed shell should always resolve through workspace policy. This keeps the command auditable and prevents accidental process execution without target scope.

## Dogfood Fixtures Should Include Negative Policy Checks

The source-readonly write attempt was useful because it confirmed the policy gate and also exposed the status aggregation bug.

## Acceptance Should Include UX Truth

It is not enough for the run to pass. Mobile/Launcher state must agree with run status, validation, artifacts and safety labels.

