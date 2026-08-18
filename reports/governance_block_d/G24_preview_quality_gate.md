# G24 - Approval Preview Quality Gate

Checkpoint: G24_APPROVAL_PREVIEW_QUALITY_GATE_READY

ApprovalPreviewQualityGate foi conectado ao lifecycle para impedir approvals genericos e nao auditaveis.

Preview de escrita valido exige:

- context_ref.
- target files/paths reais.
- executable_plan_ref.
- expected outputs.
- validation plan.
- rollback plan.
- payload de plano concreto: project_generation_plan, patch_plan ou concrete_file_operations.

Reason codes adicionados:

- PREVIEW_REJECTED_GENERIC_WRITE_ACTION.
- PREVIEW_REJECTED_NO_TARGET_FILES.
- PREVIEW_REJECTED_NO_EXECUTABLE_PLAN.
- PREVIEW_REJECTED_NO_EXPECTED_OUTPUTS.
- PREVIEW_REJECTED_NO_VALIDATION_PLAN.
- PREVIEW_REJECTED_NO_ROLLBACK_PLAN.
- PREVIEW_REJECTED_NO_CONTEXT_REF.

Evidencia:

- tests/governance/test_g24_preview_quality_gate.py
- ExecutablePlanService agora valida qualidade antes de ApprovalService criar approval.
- Matriz ampliada: 46 passed in 132.13s.

