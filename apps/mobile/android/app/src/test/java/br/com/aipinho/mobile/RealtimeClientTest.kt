package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.BackoffPolicy
class RealtimeClientTest { @Test fun backoffIsBounded(){ assertEquals(30,BackoffPolicy.seconds(99)) } }
