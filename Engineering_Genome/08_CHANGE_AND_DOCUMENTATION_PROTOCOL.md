# Change and Documentation Protocol

## Before mutation

1. Reobserve Git branch/HEAD/worktree and the current project frontier.
2. Read relevant authority, architecture, responsibility, and state documents.
3. Characterize existing behavior before refactoring it.
4. Identify the canonical owner and competing/duplicate paths.
5. Classify suspicious literals as invariant, policy, capability, context, or heuristic.
6. Define expected semantic behavior, forbidden behavior, and required evidence.

Do not “clean up” behavior that has not yet been understood.

## During implementation

Keep one canonical path. Prefer general contracts over named-case exceptions. Preserve provenance and information fidelity. Keep fallbacks subordinate. Do not weaken a gate merely because the new path cannot satisfy it; diagnose the missing contract/evidence instead.

## Validation and documentation

Run the focused regression that reproduces the behavior being changed, then broaden according to blast radius. Use real/emulator/live evidence when the claim itself concerns that surface.

Every meaningful checkpoint evaluates documentation rather than blindly editing everything: Constitution, Architecture, Responsibility map, Configuration model, Tests/evidence, ADR, Current frontier, and README should each be marked unchanged or reconciled as applicable.

A behavioral change that makes a current document false is not complete until reconciled.

## ADR rule

Create an ADR for durable architectural choices with meaningful alternatives or tradeoffs. Record context, decision, alternatives, consequences, evidence, and supersession. ADRs are not work diaries.
