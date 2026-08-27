# AIpinho — Current External Control State

_Last updated: 2026-08-27T18:15:00Z by Lucio_

## Repository role

`AIpinho` is the AIpinho runtime/application repository.

It is not the source of Control Plane authority. Canonical governance, broker, replay, authentication, shell authority, and coordination live in:

- `sasandralean-prog/AIpinho-FireTest-Control`

The AIpinho root `COMMUNICATION_SYNC.md` is a redirect/mirror marker only.

## Current external Control Plane status

- Control PR #20 merged: `CONTROL B1.0-G.1.2 — psutil identity observation shim`.
- Control PR #21 merged: `CONTROL B1.0-G.2 — governed envelope broker`.
- Control `main` after PR #21: `702726b081314fad172055b4b7342465664f039a` before later documentation-only updates.
- G.1 `lucio.shell` remains not live-validated.
- G.2 broker is implemented and merged, but broker/live request flow has not yet been live-validated.

## Sequence / replay state relevant to AIpinho operations

- `sequence=4`: consumed, rejected before shell execution due to containment proof unavailability.
- `sequence=5`: consumed, failed before result packaging due to broken `psutil` import surface.
- Next live shell smoke must use `sequence=6`.

## Do not claim yet

Do not use:

- `CONTROL_B1_0_G_1_AUTHENTICATED_LUCIO_SHELL_VALIDATED`

until both pass:

1. Fresh `sequence=6` live smoke.
2. Same-envelope replay-denial rerun with no second shell execution.

## Practical implication

AIpinho source/runtime work should continue to treat Control Plane authority as external and governed. Local AIpinho code must not bypass Control authentication, replay, provenance, or shell containment gates.
