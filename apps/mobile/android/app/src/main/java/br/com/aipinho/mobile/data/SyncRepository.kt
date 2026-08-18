package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.SyncClient
class SyncRepository(profile:ConnectionProfile,token:()->String?) { val client=SyncClient(profile,token) }
