# Runtime Transparency and Responsibility Model

## Runtime transparency

For every consequential operation, the system should be able to answer:

```text
What is happening?
Why?
Which canonical component decided it?
What input/context/configuration was used?
What authority permitted it?
What side effect was attempted?
What evidence was observed?
What was the state before and after?
Why is the final claim safe?
```

Logs are useful but are not the architecture. Prefer structured events/telemetry whose fields can be correlated across boundaries.

A useful event envelope may contain: event id, timestamp, component, phase, intent, decision, decision source, resolved configuration, side effect, evidence references, state before/after, limitations, and terminal status.

## Responsibility contract

For each substantial subsystem document: `Component`, `Owns`, `Consumes`, `Produces`, `May`, `Must not`, canonical dependencies, and evidence/telemetry.

A component that cannot state `Must not` probably has an unclear boundary.

## Canonical-path rule

Many sources may feed one resolver. Many implementations may satisfy one interface. Fallback may change implementation strategy. None creates a second authority.

When duplicated/analogous responsibilities are discovered, diagnose ownership before deleting code. Consolidation must preserve behavior proven to be intentional.
