package br.com.aipinho.mobile.models

data class DebuggerFilterState(
    val query: String = "",
    val logType: String = "events",
    val severity: String = "",
    val sourceService: String = "",
    val status: String = "",
)
