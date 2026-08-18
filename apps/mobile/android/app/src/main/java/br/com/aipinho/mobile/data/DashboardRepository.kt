package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.MonitorClient
import br.com.aipinho.mobile.network.UxClient
class DashboardRepository(profile:ConnectionProfile,token:()->String?) { val monitor=MonitorClient(profile,token); val ux=UxClient(profile,token) }
