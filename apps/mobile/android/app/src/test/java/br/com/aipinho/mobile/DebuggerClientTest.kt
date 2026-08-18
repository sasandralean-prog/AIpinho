package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.models.RawPayload
class DebuggerClientTest { @Test fun rawIsHidden(){ assertTrue(RawPayload("r","text").hiddenByDefault) } }
