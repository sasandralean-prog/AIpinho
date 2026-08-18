package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class ConnectionAutoFillTest {
    @Test fun connectionSuggestionsUseApiV1Only() {
        val source = NeonSourceContract.source("network/ConnectionClient.kt")
        assertTrue(source.contains("/api/v1/connection/suggestions"))
        assertTrue(NeonSourceContract.config("mobile_connection_policy.yaml").contains("/api/v1/connection/suggestions"))
    }
}
