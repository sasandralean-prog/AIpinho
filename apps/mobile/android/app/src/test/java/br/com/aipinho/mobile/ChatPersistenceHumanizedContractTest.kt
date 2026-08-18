package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class ChatPersistenceHumanizedContractTest {
    @Test fun chatClientUsesPersistentConversationalSendEndpoint() {
        val source = NeonSourceContract.source("network/ChatClient.kt")

        assertTrue(source.contains("/api/v1/chat/sessions/\$sessionId/send"))
        assertTrue(source.contains("recordMessage"))
    }

    @Test fun chatScreenPersistsActiveSessionAndReloadsHumanizedViewModelAfterSend() {
        val source = NeonSourceContract.source("ui/screens/ChatScreen.kt")

        assertTrue(source.contains("ChatSessionRepository"))
        assertTrue(source.contains("saveActiveSessionId"))
        assertTrue(source.contains("loadActiveSessionId"))
        assertTrue(source.contains("saveLastConversation"))
        assertTrue(source.contains("loadLastConversation"))
        assertTrue(source.contains("loadLastOperationalResult"))
        assertTrue(source.contains("loadActiveTaskRunId"))
        assertTrue(source.contains("saveLatestArtifact"))
        assertTrue(source.contains("loadLatestArtifactId"))
        assertTrue(source.contains("extractArtifactLink"))
        assertTrue(source.contains("syncLatestArtifactFromChatResponse"))
        assertTrue(source.contains("attachedArtifactIds"))
        assertTrue(source.contains("pendingArtifacts"))
        assertTrue(source.contains("reloadChatViewModel"))
        assertTrue(source.contains("reloadChatViewModelStabilized"))
        assertTrue(source.contains("expectedMessagesAfterSend"))
        assertTrue(source.contains("chatSendVisibleText"))
        assertTrue(source.contains("ChatPresentationRenderer"))
        assertTrue(source.contains("ChatAutoRefreshPolicy.pollIntervalMs"))
        assertTrue(source.contains("postDelayed(refreshRunnable"))
        assertTrue(source.contains("removeCallbacks(refreshRunnable)"))
        assertTrue(source.contains("displayMode"))
        assertTrue(source.indexOf("root.addView(stateCard)") < source.indexOf("root.addView(decisionCard)"))
        assertTrue(source.contains("decisionCard.visibility = if (displayMode == \"normal\") View.GONE else View.VISIBLE"))
        assertTrue(source.contains("decisionCard.visibility = View.GONE"))
        assertTrue(source.contains("decisionCard.visibility = View.VISIBLE"))
        assertTrue(source.contains("viewModelTerminal.visibility = View.VISIBLE"))
        assertTrue(source.contains("viewModelTerminal.visibility = View.VISIBLE"))
        assertTrue(source.contains("Limpar cockpit"))
        assertTrue(source.contains("viewModelTerminal.clear()"))
        assertTrue(source.contains("input.setText(\"\")"))
    }

    @Test fun chatClientUsesChatSpecificTimeoutPolicy() {
        val source = NeonSourceContract.source("network/ChatClient.kt")
        val policy = NeonSourceContract.source("ui/policies/ChatAutoRefreshPolicy.kt")

        assertTrue(source.contains("ChatAutoRefreshPolicy.chatRequestTimeoutMs"))
        assertTrue(policy.contains("pollIntervalMs: Long = 5_000L"))
        assertTrue(policy.contains("stabilizationAttempts"))
        assertTrue(policy.contains("chatRequestTimeoutMs"))
    }

    @Test fun terminalRendersHumanizedCardFieldsInsteadOfRawJsonFirst() {
        val source = NeonSourceContract.source("ui/cards/HumanizedViewModelTerminal.kt")

        assertTrue(source.contains("humanizedLines"))
        assertTrue(source.contains("what_is_happening"))
        assertTrue(source.contains("why_is_it_happening"))
        assertTrue(source.contains("is_it_safe"))
        assertTrue(source.contains("appendMetadata"))
        assertTrue(source.contains("fun clear("))
    }

    @Test fun chatPresentationRendererKeepsNormalChatFreeFromTechnicalKeys() {
        val source = NeonSourceContract.source("ui/cards/ChatPresentationRenderer.kt")

        assertTrue(source.contains("normalLines"))
        assertTrue(source.contains("detailsLines"))
        assertTrue(source.contains("rawLines"))
        assertTrue(source.contains("label"))
        assertTrue(source.contains("text"))
        assertTrue(source.contains("Estado"))
    }
}
