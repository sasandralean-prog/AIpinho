package br.com.aipinho.mobile.models.humanized

data class MobileTaskQueueSummary(
    val total: Int = 0,
    val active: Int = 0,
    val pending: Int = 0,
    val requiresDecision: Int = 0,
    val maxPending: Int = 0,
    val selectedTaskId: String? = null,
    val selectedApprovalId: String? = null,
    val approvalKind: String? = null,
    val linkedTaskRunId: String? = null,
    val taskApprovalsPending: Int = 0,
    val standaloneApprovalsPending: Int = 0,
)

data class MobilePipelineViewModel(
    val taskId: String?,
    val cards: List<HumanizedCardViewModel>,
    val status: String,
    val selectedTaskId: String? = null,
    val selectedApprovalId: String? = null,
    val approvalKind: String? = null,
    val linkedTaskRunId: String? = null,
    val taskApprovalsPending: Int = 0,
    val standaloneApprovalsPending: Int = 0,
    val queue: MobileTaskQueueSummary = MobileTaskQueueSummary(),
)
