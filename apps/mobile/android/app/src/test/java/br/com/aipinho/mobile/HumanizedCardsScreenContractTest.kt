package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HumanizedCardsScreenContractTest {
    @Test fun fiveScreensConsumeHumanizedViewModels() {
        val dashboard = NeonSourceContract.source("ui/screens/DashboardScreen.kt")
        val chat = NeonSourceContract.source("ui/screens/ChatScreen.kt")
        val pipeline = NeonSourceContract.source("ui/screens/PipelineScreen.kt")
        val debugger = NeonSourceContract.source("ui/screens/DebuggerScreen.kt")
        val settings = NeonSourceContract.source("ui/screens/SettingsScreen.kt")
        val combined = listOf(dashboard, chat, pipeline, debugger, settings).joinToString("\n")

        assertTrue(combined.contains("MobileViewModelClient"))
        assertTrue(combined.contains("HumanizedViewModelTerminal"))
        assertTrue(combined.contains("ChatDecisionCard"))
        assertTrue(combined.contains("ConfigCapabilityCard"))
        assertTrue(combined.contains("mobileViewModels.dashboard()"))
        assertTrue(combined.contains("mobileViewModels.pipeline()"))
        assertTrue(combined.contains("mobileViewModels.debugger()"))
        assertTrue(combined.contains("mobileViewModels.config()"))
        assertFalse(combined.contains("/v2"))
    }
}
