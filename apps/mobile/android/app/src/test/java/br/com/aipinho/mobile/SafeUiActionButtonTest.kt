package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class SafeUiActionButtonTest {
    @Test fun safeActionButtonCarriesDisabledReason() {
        val source = NeonSourceContract.source("ui/cards/SafeActionButton.kt")

        assertTrue(source.contains("enabledByPolicy"))
        assertTrue(source.contains("disabledReason"))
        assertTrue(source.contains("Safe action from backend view-model"))
    }
}

