package br.com.aipinho.mobile.models.humanized

data class HumanizedCardViewModel(
    val cardId: String,
    val screen: String,
    val cardType: String,
    val title: String,
    val severity: String,
    val status: String,
    val answers: HumanizedAnswerSet,
    val metadata: Map<String, String> = emptyMap(),
    val evidence: List<EvidenceRef> = emptyList(),
    val safeActions: List<SafeUiAction> = emptyList(),
    val rawRef: String? = null,
    val traceId: String? = null,
)

