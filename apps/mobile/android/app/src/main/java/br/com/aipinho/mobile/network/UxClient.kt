package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class UxClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun status()=get("/api/v1/ux/status")
    fun health()=get("/api/v1/ux/health")
    fun notifications()=get("/api/v1/ux/notifications")
}
