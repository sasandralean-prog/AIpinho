package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.utils.SseParser
class RealtimeClient(private val profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.realtimePort,token) {
    fun status()=get("/api/v1/realtime/status")
    fun since(cursor:String)=get("/api/v1/realtime/events/since/$cursor")
    fun parse(lines:List<String>)=SseParser.parse(lines)
    fun fallbackPath(cursor:String)="/api/v1/sync/changes?cursor=$cursor"
}
