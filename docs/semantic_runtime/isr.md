# Intermediate Semantic Representation

Sprint SR3 defines the canonical Intermediate Semantic Representation (ISR).

The ISR is independent from Runtime execution. It is the only output produced by
the Semantic Interpreter and exists before operation contracts, task drafts,
approvals, tools, skills, patches, or execution.

## Canonical Fields

- `version`
- `intent`
- `entities`
- `scope`
- `permissions_requested`
- `constraints`
- `expected_outputs`
- `ambiguity`
- `confidence`
- `semantic_trace`
- `metadata`
- `extensions`

## Versioning

The current version is `1.0`.

Future schema expansion must use compatible fields or the `extensions` object
instead of forcing downstream consumers to depend on prompt text or Runtime
objects.

## Validation

`ISRValidator` checks:

- supported version
- structural validity
- confidence range
- ambiguity shape
- no side effects
- no runtime refs such as `task_id` or `approval_id`

## Serialization

`ISRSerializer` provides stable JSON/dict round-tripping for audit and future
cross-process use.

## Boundary

No step after semantic interpretation should consume the raw prompt directly.
Later sprints may migrate downstream stages to consume ISR, but SR3 does not
create contracts or execute Runtime.
