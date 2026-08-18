package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class ContextClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun status()=get("/api/v1/context/status")
    fun explain(bundleId:String)=get("/api/v1/context/bundles/$bundleId/explain")
}
