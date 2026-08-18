package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatCopyActionsTest {
    @Test fun chatProvidesCopyAndKeepsRawSeparate() {
        val source = NeonSourceContract.source("ui/screens/ChatScreen.kt")
        assertTrue(source.contains("NeonRawCopyButton"))
        assertTrue(source.contains("Anexar"))
        assertTrue(source.contains("attachedArtifactIds"))
        assertTrue(source.contains("chat.send(activeSessionId ?: \"\", text, pendingArtifacts)"))
        assertTrue(source.contains("ArtifactLinkRenderer"))
        assertTrue(source.contains("renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer)"))
        assertFalse(source.contains("Copiar conversa"))
        assertFalse(source.contains("Gerar ZIP"))
        assertFalse(source.contains("Exportar resumo"))
        assertFalse(source.contains("Baixar resumo.zip"))
        assertTrue(source.contains("ChatSessionIdExtractor.extract"))
        assertFalse(source.contains("/v2"))
    }
}
