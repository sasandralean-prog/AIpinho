package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.PipelineClient
class PipelineRepository(profile:ConnectionProfile,token:()->String?) { val client=PipelineClient(profile,token) }
