package br.com.aipinho.mobile.models

data class ConnectionAutoFillState(
    val source: String,
    val host: String?,
    val detected: Boolean,
    val ports: Map<String, Int> = emptyMap(),
    val humanMessage: String = "",
)
