package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class EventClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun status()=get("/api/v1/events/status")
    fun contracts()=get("/api/v1/events/contracts")
    fun events()=get("/api/v1/events")
    fun event(eventId:String)=get("/api/v1/events/$eventId")
}
