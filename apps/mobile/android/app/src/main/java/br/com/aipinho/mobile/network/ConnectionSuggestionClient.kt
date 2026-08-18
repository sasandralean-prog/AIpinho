package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile

class ConnectionSuggestionClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.monitorPort, token) {
    fun suggestions() = get("/api/v1/connection/suggestions")
}
