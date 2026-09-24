# Configuration and Semantic Cache Model

## Resolution contract

Context-sensitive configuration should resolve through an observable pipeline:

```text
defaults/invariants
→ project policy
→ environment/capability discovery
→ mission or user scope
→ runtime validation
→ effective value
```

An effective value should be explainable with `value`, `source`, `scope`, relevant `context`, `validated_at` when meaningful, and whether it is frozen for the current operation.

Precedence must be explicit. A lower-authority source must not silently override a stronger safety, resource, or user constraint.

## Dynamic configuration

Prefer typed configuration and capability discovery over scattered literals. Do not move every constant into a config file: invariants belong in contracts/code. Configuration without ownership, validation, or provenance merely relocates hardcode.

## Semantic cache

Separate caches by semantics rather than building one opaque cache: interpretation, capability, discovery/provider, and evidence/artifact caches.

Keys should include semantic inputs that can change validity, such as contract/schema version, project revision, relevant configuration fingerprint, capability/environment fingerprint, and normalized semantic input.

Invalidation is part of the cache contract. Historical immutable evidence may be retained indefinitely; capability and discovery claims usually require revalidation. Cache contents never grant permission, policy authority, or runtime truth.
