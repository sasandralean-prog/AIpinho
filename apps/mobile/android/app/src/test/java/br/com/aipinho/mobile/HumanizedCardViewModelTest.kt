package br.com.aipinho.mobile

import br.com.aipinho.mobile.models.humanized.EvidenceRef
import br.com.aipinho.mobile.models.humanized.HumanizedAnswerSet
import br.com.aipinho.mobile.models.humanized.HumanizedCardViewModel
import br.com.aipinho.mobile.models.humanized.SafetyState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HumanizedCardViewModelTest {
    @Test fun cardModelCarriesSixDogmaAnswers() {
        val evidence = EvidenceRef("event", "event_1", "Evento 1")
        val card = HumanizedCardViewModel(
            cardId = "card_1",
            screen = "dashboard",
            cardType = "status",
            title = "Core",
            severity = "info",
            status = "healthy",
            answers = HumanizedAnswerSet(
                whatIsHappening = "Core esta online.",
                whyIsItHappening = "Health respondeu.",
                isItSafe = SafetyState("safe", "Read-only."),
                whatCanIDoNow = listOf("Copiar resumo."),
                whatEvidenceSupportsThis = listOf(evidence),
                canCopySanitizedSummary = true,
            ),
        )

        assertEquals("dashboard", card.screen)
        assertTrue(card.answers.canCopySanitizedSummary)
        assertEquals("event_1", card.answers.whatEvidenceSupportsThis.first().refId)
    }
}

