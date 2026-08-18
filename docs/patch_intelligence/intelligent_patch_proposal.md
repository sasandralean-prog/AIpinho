# Intelligent Patch Proposal

The Intelligent Patch Proposal layer composes Runtime Doctor evidence, Regression Matrix rows, Pattern Matches, Patch Knowledge Base entries, and advisory Patch Plans into a structured proposal for an external operator.

It never modifies files, generates final code, emits `apply_patch`, commits changes, or executes tools.

## Components

- `IntelligentPatchProposalService`
- `PatchProposalBuilder`
- `PatchProposalValidator`
- `PatchProposalSerializer`

## Inputs

- `RuntimeDoctorReport`
- `RegressionMatrix`
- `PatchPatternMatch`
- `PatchKnowledgeBase`
- `PatchPlan`

## Output

`IntelligentPatchProposal` containing:

- proposal id;
- covered regressions;
- patterns used;
- candidate modules;
- candidate files;
- justification;
- suggested strategy;
- risks;
- recommended rollback;
- required tests;
- confidence;
- knowledge entry references;
- patch plan references.

## Safety

The proposal is executor independent:

- no code generation;
- no `apply_patch`;
- no commit;
- no automatic runtime modification;
- no direct coupling to Codex, Gemini, Mobile, Launcher, or any future operator.

## Endpoints

- `POST /api/v1/runtime/patch-intelligence/proposal`
- `GET /api/v1/runtime/patch-intelligence/proposal/{id}`
