package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MobileViewModelClientTest {
    @Test fun clientUsesApiV1MobileViewModelEndpointsOnly() {
        val source = NeonSourceContract.source("network/MobileViewModelClient.kt")

        assertTrue(source.contains("/api/v1/mobile/view-model/status"))
        assertTrue(source.contains("/api/v1/mobile/view-model/dashboard"))
        assertTrue(source.contains("/api/v1/mobile/view-model/agents"))
        assertTrue(source.contains("/api/v1/mobile/view-model/chat/"))
        assertTrue(source.contains("/api/v1/mobile/view-model/pipeline"))
        assertTrue(source.contains("/api/v1/mobile/view-model/debugger"))
        assertTrue(source.contains("/api/v1/mobile/view-model/config"))
        assertFalse(source.contains("/v2"))
    }

    @Test fun mobileExposesAgentMarketplaceScreenWithoutProviderBranches() {
        val navigation = NeonSourceContract.source("ui/navigation/MainNavigationState.kt")
        val main = NeonSourceContract.source("MainActivity.kt")
        val screen = NeonSourceContract.source("ui/screens/AgentMarketplaceScreen.kt")

        assertTrue(navigation.contains("AGENTS(\"Agentes\""))
        assertTrue(main.contains("AgentMarketplaceScreen"))
        assertTrue(screen.contains("Agent Marketplace"))
        assertTrue(screen.contains("client.agents()"))
        assertFalse(screen.lowercase().contains("if gemini"))
        assertFalse(screen.lowercase().contains("if codex"))
    }
}
