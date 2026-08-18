package br.com.aipinho.mobile.utils

object ChatSessionIdExtractor {
    private val sessionFields = listOf(
        Regex(""""session_id"\s*:\s*"((?:chat|session)_[A-Za-z0-9-]+)""""),
        Regex(""""chat_session_id"\s*:\s*"((?:chat|session)_[A-Za-z0-9-]+)""""),
    )

    fun extract(value: String): String? {
        return sessionFields.firstNotNullOfOrNull { pattern ->
            pattern.find(value)?.groupValues?.getOrNull(1)
        }
    }
}
