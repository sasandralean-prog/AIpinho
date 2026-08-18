package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatClientTest {
    @Test fun mobileHasNoModelExecutionFlag() {
        assertFalse(AppConfig.restartAllowedPorts.contains(9099))
    }

    @Test fun chatSendUsesBackendContentField() {
        val source = NeonSourceContract.source("network/ChatClient.kt")
        assertTrue(source.contains("\\\"content\\\""))
        assertFalse(source.contains("\\\"text\\\":"))
    }

    @Test fun chatClientUsesSharedJsonPayloadEscaper() {
        val source = NeonSourceContract.source("network/ChatClient.kt")
        assertTrue(source.contains("JsonPayload.string(value)"))
    }

    @Test fun chatClientSupportsSessionManagementActions() {
        val clientSource = NeonSourceContract.source("network/ChatClient.kt")
        val baseSource = NeonSourceContract.source("network/BaseApiClient.kt")
        val screenSource = NeonSourceContract.source("ui/screens/ChatScreen.kt")

        assertTrue(baseSource.contains("fun patch(path:String"))
        assertTrue(baseSource.contains("fun delete(path:String)"))
        assertTrue(clientSource.contains("renameSession"))
        assertTrue(clientSource.contains("deleteSession"))
        assertTrue(clientSource.contains("/api/v1/chat/sessions?limit=50"))
        assertTrue(clientSource.contains("/api/v1/chat/sessions/\$sessionId"))
        assertTrue(screenSource.contains("showSessionsDialog"))
        assertTrue(screenSource.contains("showRenameSessionDialog"))
        assertTrue(screenSource.contains("Abrir"))
        assertTrue(screenSource.contains("Renomear"))
        assertTrue(screenSource.contains("Deletar"))
    }
}

