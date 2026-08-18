package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.RealtimeClient
class RealtimeRepository(profile:ConnectionProfile,token:()->String?) { val client=RealtimeClient(profile,token); private val seen=mutableSetOf<String>(); fun accept(eventId:String)=seen.add(eventId) }
