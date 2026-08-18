# Patch Intelligence Pattern Engine

The Pattern Engine recognizes recurring runtime regression patterns from canonical runtime structures.

It does not read prompts and does not match full text.

## Components

- `PatchPatternEngine`
- `PatternMatcher`
- `PatternNormalizer`
- `PatternScorer`
- `PatternConfidenceCalculator`

## Inputs

- `RuntimeDoctorReport`
- `RegressionMatrix`
- `PatchKnowledgeBase`

## Output

`PatchPatternMatch` with:

- pattern id;
- confidence;
- related regressions;
- suspected modules;
- recommended strategy;
- justification;
- risks.

## Matching Rules

Recognition uses only:

- regression category;
- matrix status;
- reason code;
- structured suspected modules;
- knowledge base metadata.

It does not use:

- prompt text;
- full message text;
- project-specific paths;
- Fire Test hardcodes.

## Endpoints

- `GET /api/v1/runtime/patch-intelligence/patterns`
- `POST /api/v1/runtime/patch-intelligence/patterns`
