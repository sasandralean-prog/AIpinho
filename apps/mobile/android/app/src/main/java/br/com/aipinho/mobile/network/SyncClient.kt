package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
class SyncClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun snapshot()=get("/api/v1/sync/snapshot")
    fun changes(cursor:String)=get("/api/v1/sync/changes?cursor=$cursor")
}
