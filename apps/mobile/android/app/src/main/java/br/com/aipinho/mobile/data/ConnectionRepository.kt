package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.BaseApiClient
import br.com.aipinho.mobile.network.ApiResponse
class ConnectionRepository(private val token:()->String?) {
    fun test(profile:ConnectionProfile):Map<Int,ApiResponse> = listOf(profile.corePort,profile.realtimePort,profile.artifactPort,profile.monitorPort).associateWith { BaseApiClient(profile,it,token).get("/api/v1/health") }
}
