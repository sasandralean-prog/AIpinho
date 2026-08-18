package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.ui.policies.ChatAutoRefreshPolicy

class ChatClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token,ChatAutoRefreshPolicy.chatRequestTimeoutMs) {
    fun sessions()=get("/api/v1/chat/sessions?limit=50")
    fun createSession()=post("/api/v1/chat/sessions")
    fun renameSession(sessionId:String,title:String)=post("/api/v1/chat/sessions/$sessionId/rename","{\"title\":${json(title)}}")
    fun deleteSession(sessionId:String)=delete("/api/v1/chat/sessions/$sessionId")
    fun timeline(sessionId:String)=get("/api/v1/chat/sessions/$sessionId/timeline")
    fun recordMessage(sessionId:String,text:String)=post("/api/v1/chat/sessions/$sessionId/messages","{\"content\":${json(text)}}")
    fun send(sessionId:String,text:String,artifactIds:List<String> = emptyList()):ApiResponse {
        val metadata = if (artifactIds.isEmpty()) "{}" else "{\"attached_artifact_ids\":[${artifactIds.joinToString(","){json(it)}}]}"
        return post("/api/v1/chat/sessions/$sessionId/send","{\"content\":${json(text)},\"metadata\":$metadata}")
    }
    fun feedback(messageId:String,value:String,reason:String)=post("/api/v1/chat/messages/$messageId/feedback","{\"value\":${json(value)},\"reason\":${json(reason)}}")
    private fun json(value:String)=JsonPayload.string(value)
}


