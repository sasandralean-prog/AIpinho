package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.SseParser
class SseParserTest { @Test fun parsesEvent(){ val e=SseParser.parse(listOf("id: 1","event: update","data: ok","")); assertEquals("1",e.first().id) } }
