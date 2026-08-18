package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.ChatClient
class ChatRepository(profile:ConnectionProfile,token:()->String?) { val client=ChatClient(profile,token) }
