package br.com.aipinho.mobile

import br.com.aipinho.mobile.utils.ChatSessionIdExtractor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ChatSessionIdExtractorTest {
    @Test fun extractsSessionIdValueFromCreateSessionResponse() {
        val body = """{"session":{"session_id":"chat_abc123","status":"active"}}"""

        assertEquals("chat_abc123", ChatSessionIdExtractor.extract(body))
    }

    @Test fun doesNotReturnJsonKeyAsSessionId() {
        val body = """{"session_id":"chat_abc123"}"""

        assertEquals("chat_abc123", ChatSessionIdExtractor.extract(body))
    }

    @Test fun acceptsSessionPrefixValue() {
        val body = """{"session":{"session_id":"session_abc-123"}}"""

        assertEquals("session_abc-123", ChatSessionIdExtractor.extract(body))
    }

    @Test fun returnsNullWhenNoSessionFieldExists() {
        val body = """{"status":"ok","message":"no session here"}"""

        assertNull(ChatSessionIdExtractor.extract(body))
    }
}
