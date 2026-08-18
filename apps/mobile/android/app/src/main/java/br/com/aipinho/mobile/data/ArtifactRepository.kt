package br.com.aipinho.mobile.data
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.network.ArtifactClient
class ArtifactRepository(profile:ConnectionProfile,token:()->String?) { val client=ArtifactClient(profile,token) }
