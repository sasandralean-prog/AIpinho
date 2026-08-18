package br.com.aipinho.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class TokenRedactionTest {
    @Test fun copiedTechnicalTextRedactsBearerTokens() {
        val redacted = br.com.aipinho.mobile.utils.Redaction.redact("Authorization: Bearer abc.def.ghi")
        assertFalse(redacted.contains("abc.def.ghi"))
        assertEquals("Authorization: Bearer [REDACTED]", redacted)
    }
}
