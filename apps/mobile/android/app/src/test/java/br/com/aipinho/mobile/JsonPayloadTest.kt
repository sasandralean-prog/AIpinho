package br.com.aipinho.mobile

import br.com.aipinho.mobile.network.JsonPayload
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class JsonPayloadTest {
    @Test fun escapesMultilineChatTextAsJsonString() {
        val encoded = JsonPayload.string("linha 1\nC:\\Projeto\\arquivo \"x\"\r\tfim")
        assertEquals("\"linha 1\\nC:\\\\Projeto\\\\arquivo \\\"x\\\"\\r\\tfim\"", encoded)
        assertFalse(encoded.substring(1, encoded.length - 1).contains("\n"))
        assertFalse(encoded.substring(1, encoded.length - 1).contains("\r"))
    }

    @Test fun escapesControlCharactersWithoutDroppingContent() {
        val encoded = JsonPayload.string("a\u0001b")
        assertEquals("\"a\\u0001b\"", encoded)
    }
}
