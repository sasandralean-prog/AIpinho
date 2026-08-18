package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.Redaction
class RedactionTest { @Test fun redactsApiKey(){ assertEquals("[REDACTED_SECRET]",Redaction.redact("sk-abcdefghijklmnop")) } }
