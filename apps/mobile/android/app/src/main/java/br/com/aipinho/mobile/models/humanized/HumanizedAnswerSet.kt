package br.com.aipinho.mobile.models.humanized

data class SafetyState(
    val answer: String,
    val reason: String,
)

data class HumanizedAnswerSet(
    val whatIsHappening: String,
    val whyIsItHappening: String,
    val isItSafe: SafetyState,
    val whatCanIDoNow: List<String>,
    val whatEvidenceSupportsThis: List<EvidenceRef>,
    val canCopySanitizedSummary: Boolean,
)

