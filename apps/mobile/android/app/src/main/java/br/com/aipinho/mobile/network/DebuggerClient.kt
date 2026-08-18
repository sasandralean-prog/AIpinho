package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class DebuggerClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun status()=get("/api/v1/debugger/status")
    fun timeline(traceId:String)=get("/api/v1/debugger/traces/$traceId/timeline")
    fun raw(rawRef:String)=get("/api/v1/raw/$rawRef/viewer")
}
