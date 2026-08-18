package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.DebuggerClient
class DebuggerRepository(profile:ConnectionProfile,token:()->String?) { val client=DebuggerClient(profile,token) }
