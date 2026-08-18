package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile

class MobileEvidenceClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.corePort, token) {
    fun evidence(type: String, refId: String) = get("/api/v1/mobile/view-model/evidence/$type/$refId")
}

