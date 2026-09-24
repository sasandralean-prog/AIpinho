# Semantic Testing Philosophy

## Test the story, not only the function

For behavior-changing work, express proof as:

```text
context
→ initial state
→ intent/action
→ expected semantic effect
→ forbidden effects
→ evidence produced
→ final truth
```

A green unit test is bounded evidence, not automatic proof of public/runtime behavior.

## Test families

Use the smallest useful combination of contract tests, behavioral regression tests, negative tests, metamorphic tests, property tests, integration tests, and E2E/runtime tests.

Important fixes should include a regression that reproduces the old behavior and proves the intended replacement behavior—not merely a test that prevents the exact old implementation from returning.

## Metamorphic examples

Renaming a workspace should not change mission meaning. A misleading media extension should not outrank physical container evidence. Reordering unrelated providers should not change canonical identity. Rephrasing an instruction without changing authority should not silently widen scope.

## Evidence discipline

Record what a test proves and what it does not. Distinguish static inspection, deterministic test evidence, emulator/sandbox evidence, and live/manual evidence. Never promote a narrower proof into a broader verdict without new evidence.
