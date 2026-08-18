# Diagnosis Quality

## Status

READY

## Autoridade observada

`CanonicalDiagnosisArtifact`

## Analyzer

`DiagnosisQualityAnalyzer`

## Campos avaliados

- simbolo;
- arquivo alvo;
- comportamento observado;
- comportamento esperado;
- hipotese;
- confidence;
- evidencia.

## Saida

`QualityAnalysis` com:

- score 0-100;
- confidence baixa/media/alta;
- campos presentes;
- campos ausentes;
- reason_codes;
- diagnostics.

## Reason code principal

`DIAGNOSIS_TOO_GENERIC`

O analyzer nao bloqueia. Ele explica qualidade. Bloqueios continuam nas autoridades ja existentes.
