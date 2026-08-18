package br.com.aipinho.mobile.ui.policies

object ChatAutoRefreshPolicy {
    const val pollIntervalMs: Long = 5_000L
    const val operationFeedbackHoldMs: Long = 15_000L
    const val stabilizationAttempts: Int = 4
    const val stabilizationDelayMs: Long = 900L
    const val chatRequestTimeoutMs: Int = 20_000
}
