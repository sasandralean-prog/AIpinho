package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class ConnectionClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.monitorPort,token) {
    fun profiles()=get("/api/v1/connection/profiles")
    fun suggestions()=get("/api/v1/connection/suggestions")
    fun select(profileId:String)=post("/api/v1/connection/profiles/select","{\"profile_id\":\"$profileId\"}")
    fun adbCommands()=get("/api/v1/connection/adb/reverse-commands")
    fun pairingStatus()=get("/api/v1/mobile/pairing/status")
    fun verifyPairing()=post("/api/v1/mobile/pairing/verify")
}
