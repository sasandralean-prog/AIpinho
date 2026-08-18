package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class DebuggerFilterPanelTest {
    @Test fun debuggerHasFilterAndRawCopyControls() {
        val source = NeonSourceContract.source("ui/screens/DebuggerScreen.kt")
        val terminal = NeonSourceContract.source("ui/cards/HumanizedViewModelTerminal.kt")
        assertTrue(source.contains("HumanizedViewModelTerminal"))
        assertTrue(source.contains("mobileViewModels.debugger()"))
        assertTrue(source.contains("debuggerTrace"))
        assertTrue(terminal.contains("eventos"))
        assertTrue(terminal.contains("raw_ref"))
    }
}
