package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class HumanizedViewModelTerminalTest {
    @Test fun terminalProvidesFiltersForTimelineEventsEvidenceActionsAndRawRefs() {
        val source = NeonSourceContract.source("ui/cards/HumanizedViewModelTerminal.kt")

        assertTrue(source.contains("todos"))
        assertTrue(source.contains("eventos"))
        assertTrue(source.contains("evidencia"))
        assertTrue(source.contains("acoes"))
        assertTrue(source.contains("timeline"))
        assertTrue(source.contains("raw_ref"))
        assertTrue(source.contains("NeonTerminalCard"))
        assertTrue(source.contains("copyText"))
    }
}
