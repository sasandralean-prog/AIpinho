# Patch Candidate Quality

## Status

READY

## Autoridade observada

`PatchCandidateArtifact`

## Analyzer

`PatchCandidateQualityAnalyzer`

## Campos avaliados

- target_file;
- target_symbol;
- observed_behavior;
- expected_behavior;
- evidence_refs;
- confidence;
- diagnosis_id;
- current_content_excerpt.

## Saida

`QualityAnalysis` e anexado ao `candidate.technical_context.patch_candidate_quality`.

## Reason code principal

`PATCH_CANDIDATE_TOO_WEAK`

O analyzer nao cria replacement, diff, rollback ou approval.
