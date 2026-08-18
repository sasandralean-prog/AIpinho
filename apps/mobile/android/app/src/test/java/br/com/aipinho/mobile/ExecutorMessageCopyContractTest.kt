package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class ExecutorMessageCopyContractTest {
    @Test
    fun codexAndGeminiMessagesAreSelectableAndCopyable() {
        val support = NeonSourceContract.source("ui/components/MessageCopySupport.kt")
        val sharedAgentTab = NeonSourceContract.source("ui/screens/AgentTabScreen.kt")
        val codex = NeonSourceContract.source("ui/screens/CodexAgentScreen.kt")
        val gemini = NeonSourceContract.source("ui/screens/GeminiExecutorScreen.kt")

        assertTrue(support.contains("setTextIsSelectable(true)"))
        assertTrue(support.contains("ClipboardUtils.copy"))
        assertTrue(support.contains("selectionStart"))
        assertTrue(support.contains("latestMessage"))

        assertTrue(sharedAgentTab.contains("setTextIsSelectable(true)"))
        assertTrue(sharedAgentTab.contains("\"Copiar mensagem\""))
        assertTrue(sharedAgentTab.contains("\"Copiar conversa\""))
        assertTrue(sharedAgentTab.contains("\"Exportar\""))
        assertTrue(sharedAgentTab.contains("\"Expandir\""))
        assertTrue(sharedAgentTab.contains("\"Buscar na conversa\""))
        assertTrue(sharedAgentTab.contains("\"Nova mensagem\""))
        assertTrue(sharedAgentTab.contains("lastRenderedTimelineText"))
        assertTrue(sharedAgentTab.contains("!timelineScroll.canScrollVertically(1)"))
        assertTrue(sharedAgentTab.contains("copySelectionOrLatest"))
        assertTrue(sharedAgentTab.contains("ClipboardUtils.copy"))
        assertTrue(sharedAgentTab.contains("latestAssistantMessage"))
        assertTrue(codex.contains("AgentTabScreen"))
        assertTrue(gemini.contains("AgentTabScreen"))
    }
}
