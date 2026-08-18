package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class NeonTerminalCardTest {
    @Test fun terminalCardKeepsScrollableLogArea() {
        val source = NeonSourceContract.source("ui/components/NeonTerminalCard.kt")
        val logTerminal = NeonSourceContract.source("ui/components/NeonLogTerminal.kt")
        assertTrue(source.contains("NeonLogTerminal"))
        assertTrue(source.contains("setLines"))
        assertTrue(logTerminal.contains("ScrollView"))
        assertTrue(logTerminal.contains("isVerticalScrollBarEnabled = true"))
        assertTrue(logTerminal.contains("isNestedScrollingEnabled = true"))
        assertTrue(logTerminal.contains("setTextIsSelectable(true)"))
    }
}
