package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MultiAgentMobileUiContractTest {
    @Test
    fun sharedAgentTabOwnsScrollableChatAndGovernedSessionActions() {
        val tab = NeonSourceContract.source("ui/screens/AgentTabScreen.kt")
        val dialogs = NeonSourceContract.source("ui/components/NeonAgentDialogs.kt")
        val repository = NeonSourceContract.source("data/AgentSessionRepository.kt")

        assertTrue(tab.contains("ScrollView"))
        assertTrue(tab.contains("TerminalScrollView"))
        assertTrue(tab.contains("requestDisallowInterceptTouchEvent"))
        assertFalse(tab.contains("scrollToBottom()"))
        assertFalse(tab.contains("initialScrollPending"))
        assertTrue(tab.contains("Sessoes"))
        assertTrue(tab.contains("Cancelar run"))
        assertTrue(tab.contains("normal"))
        assertTrue(tab.contains("details"))
        assertTrue(tab.contains("raw"))
        assertTrue(tab.contains("content_sanitized"))
        assertTrue(tab.contains("body"))
        assertTrue(tab.contains("copy_text"))
        assertTrue(tab.contains("renderDelegation"))
        assertTrue(tab.contains("Resposta direta do Provider"))
        assertTrue(tab.contains("Sem delegacao"))
        assertTrue(tab.contains("Delegation ID:"))
        assertTrue(dialogs.contains("Nova sessao"))
        assertTrue(dialogs.contains("Renomear"))
        assertTrue(dialogs.contains("Deletar"))
        assertTrue(dialogs.contains("NeonCyberCard"))
        assertTrue(repository.contains("selected_session_"))
    }

    @Test
    fun agentClientKeepsSecretsOutOfUrlsAndUsesOfficialNamespaces() {
        val source = NeonSourceContract.source("network/AgentApiClient.kt")

        assertTrue(source.contains("/api/v1/agents/"))
        assertTrue(source.contains("/artifacts/upload"))
        assertTrue(source.contains("/view-model"))
        assertFalse(source.contains("OPENAI_API_KEY"))
        assertFalse(source.contains("GEMINI_API_KEY"))
        assertFalse(source.contains("?token="))
        assertFalse(source.contains("Authorization="))
    }
}
