package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile

class MobileSupportBundleClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.corePort, token) {
    fun preview() = get("/api/v1/mobile/view-model/support-bundle/preview")
}

