package br.com.aipinho.mobile.models

data class ChatCopyState(
    val messageId: String,
    val canCopyMessage: Boolean = true,
    val canCopyResponse: Boolean = true,
    val rawAvailable: Boolean = false,
    val rawSanitizedOnly: Boolean = true,
)
