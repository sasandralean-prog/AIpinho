package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.Redaction
class TokenRepositoryTest { @Test fun tokenIsRedacted(){ assertFalse(Redaction.redact("Bearer secret-token-value").contains("secret-token-value")) } }
