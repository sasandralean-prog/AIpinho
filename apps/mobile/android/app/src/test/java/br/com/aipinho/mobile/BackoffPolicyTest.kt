package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.BackoffPolicy
class BackoffPolicyTest { @Test fun scheduleStartsAtOne(){ assertEquals(1,BackoffPolicy.seconds(0)) } }
