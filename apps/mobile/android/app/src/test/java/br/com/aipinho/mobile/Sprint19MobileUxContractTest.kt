package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Sprint19MobileUxContractTest {
    @Test
    fun mainActivityDoesNotOwnGlobalVerticalScroll() {
        val source = NeonSourceContract.source("MainActivity.kt")
        assertFalse(source.contains("ScrollView(this).apply { addView(content) }"))
        assertTrue(source.contains("FrameLayout"))
    }

    @Test
    fun screensOwnScrollingAndActionsUseTwoColumnGroups() {
        val scaffold = NeonSourceContract.source("ui/components/MobileScreenScaffold.kt")
        val actions = NeonSourceContract.source("ui/components/NeonActionGroup.kt")
        val agent = NeonSourceContract.source("ui/screens/AgentTabScreen.kt")
        val chat = NeonSourceContract.source("ui/screens/ChatScreen.kt")

        assertTrue(scaffold.contains("ScrollView"))
        assertTrue(actions.contains("chunked(2)"))
        assertTrue(agent.contains("MobileScreenScaffold"))
        assertTrue(agent.contains("NeonActionGroup"))
        assertTrue(chat.contains("MobileScreenScaffold"))
        assertTrue(chat.contains("NeonActionGroup"))
    }

    @Test
    fun allAgentTabsExposeUniversalArtifactsWithoutSecretUrls() {
        val panel = NeonSourceContract.source("ui/components/AgentArtifactPanel.kt")
        val client = NeonSourceContract.source("network/ArtifactDownloadManager.kt")
        val agent = NeonSourceContract.source("ui/screens/AgentTabScreen.kt")

        assertTrue(agent.contains("AgentArtifactPanel"))
        assertTrue(panel.contains("Entradas anexadas"))
        assertTrue(panel.contains("Nenhum artifact gerado"))
        assertTrue(panel.contains("downloadEndpoint"))
        assertTrue(panel.contains("\"ready\""))
        assertTrue(panel.contains("Pronto para download"))
        assertTrue(panel.contains("Falhou:"))
        assertTrue(panel.contains("Bloqueado:"))
        assertTrue(client.contains("Authorization"))
        assertFalse(client.contains("?token="))
    }

    @Test
    fun terminalKeepsManualScrollWithoutAutomaticRepositioning() {
        val terminal = NeonSourceContract.source("ui/components/NeonLogTerminal.kt")
        assertTrue(terminal.contains("requestDisallowInterceptTouchEvent"))
        assertFalse(terminal.contains("scrollToLatest()"))
        assertFalse(terminal.contains("keepFollowing"))
    }
}
