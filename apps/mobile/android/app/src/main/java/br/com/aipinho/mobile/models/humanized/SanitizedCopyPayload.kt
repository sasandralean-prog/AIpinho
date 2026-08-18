package br.com.aipinho.mobile.models.humanized

data class SanitizedCopyPayload(
    val cardId: String,
    val summary: String,
    val metadata: Map<String, String> = emptyMap(),
    val evidence: List<EvidenceRef> = emptyList(),
    val copyPolicy: String = "sanitized_only",
    val containsSecret: Boolean = false,
)

