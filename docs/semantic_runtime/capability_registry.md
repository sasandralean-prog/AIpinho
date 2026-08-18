# Semantic Runtime Capability Registry

Sprint SR1 introduces a canonical semantic selection layer for model use.

The Runtime must request capabilities, not concrete model paths. Concrete model
selection is now mediated by:

- `SemanticCapabilityRegistry`
- `CapabilityResolver`
- `ModelPolicyResolver`
- existing `ModelRegistryService`

## Flow

```text
Role / Runtime need
  -> capability id
  -> CapabilityResolver
  -> SemanticCapabilityRegistry
  -> ModelPolicyResolver
  -> ModelRegistryService / ProviderRegistryService
  -> selected model id
```

## Capability Contracts

Capability contracts live in:

`config/semantic_runtime/capability_registry.yaml`

Each contract declares:

- `capability_id`
- display name
- aliases
- required model capabilities
- primary model
- fallback models
- escalation models
- enabled/disabled state

Supported initial capabilities include semantic understanding, planning, code
generation, code review, vision, OCR, embedding, reranking, conversation,
reporting, and debugging.

## Compatibility

Existing role model bindings remain valid. SR1 does not change Runtime behavior:
role bindings are merged into capability bindings and resolved through the new
registry. This avoids direct model selection in the role gate while preserving
the current defaults.

## Selection States

The resolver can return:

- `primary`
- `fallback`
- `escalation`
- `disabled`
- `unavailable`
- `blocked`
- `requested`

Disabled capabilities do not select models. Unavailable capabilities report a
structured reason instead of silently falling back.

## Non-goals

SR1 does not implement the Semantic Interpreter, new planning behavior, or any
new runtime workflow.
