package br.com.aipinho.mobile.models
data class ChatMessage(val messageId:String,val sessionId:String,val role:String,val text:String,val status:String="sent",val artifactLinks:List<ArtifactLink> = emptyList(),val rawRef:String?=null)
