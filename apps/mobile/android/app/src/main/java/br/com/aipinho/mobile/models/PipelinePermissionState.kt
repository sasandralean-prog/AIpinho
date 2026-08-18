package br.com.aipinho.mobile.models

data class PipelinePermissionState(
    val taskId: String,
    val requestedAction: String,
    val requiredCapability: String,
    val approvalRequired: Boolean,
    val autoGateStatus: String,
    val reason: String,
    val riskLevel: String,
    val nextSafeAction: String,
)
