package br.com.aipinho.mobile.models.humanized

data class SafeUiAction(
    val actionId: String,
    val label: String,
    val kind: String,
    val risk: String,
    val requiresConfirmation: Boolean,
    val requiresApproval: Boolean,
    val enabled: Boolean,
    val disabledReason: String?,
    val endpointRef: String,
    val method: String,
    val sideEffect: Boolean,
    val humanExplanation: String,
)

