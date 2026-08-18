package br.com.aipinho.mobile.models.humanized

data class EvidenceRef(
    val type: String,
    val refId: String,
    val humanLabel: String,
    val sanitized: Boolean = true,
)

