package br.com.aipinho.mobile

import br.com.aipinho.mobile.utils.SafeUrlBuilder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BaseApiClientTest {
    @Test fun buildsConfiguredHostOnly() {
        assertEquals("http://127.0.0.1:9088/api/v1/health", SafeUrlBuilder.build("127.0.0.1", 9088, "/api/v1/health"))
    }

    @Test fun declaresUtf8JsonTransportContract() {
        val source = NeonSourceContract.source("network/BaseApiClient.kt")
        assertTrue(source.contains("application/json; charset=utf-8"))
        assertTrue(source.contains("bufferedReader(Charsets.UTF_8)"))
        assertTrue(source.contains("toByteArray(Charsets.UTF_8)"))
    }
}
