package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.ui.policies.ChatAutoRefreshPolicy

class GeminiExecutorClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.corePort, token, ChatAutoRefreshPolicy.chatRequestTimeoutMs) {
    fun health() = get("/api/v1/gemini-executor/health")
    fun configStatus() = get("/api/v1/gemini-executor/config/status")
    fun sessions() = get("/api/v1/gemini-executor/sessions")
    fun createSession() = post("/api/v1/gemini-executor/sessions", "{\"title\":\"Gemini Executor\"}")
    fun renameSession(sessionId: String, title: String) = post("/api/v1/gemini-executor/sessions/$sessionId/rename", "{\"title\":${JsonPayload.string(title)}}")
    fun deleteSession(sessionId: String) = delete("/api/v1/gemini-executor/sessions/$sessionId")
    fun messages(sessionId: String) = get("/api/v1/gemini-executor/sessions/$sessionId/messages")
    fun send(sessionId: String, prompt: String, workspace: String = "") = post(
        "/api/v1/gemini-executor/sessions/$sessionId/send",
        payload(sessionId, prompt, workspace, "gemini_chat", emptyList())
    )
    fun plan(sessionId: String, prompt: String, workspace: String = "") = post(
        "/api/v1/gemini-executor/sessions/$sessionId/plan",
        payload(sessionId, prompt, workspace, "gemini_coding_plan", if (workspace.isBlank()) emptyList() else listOf("read_workspace", "scan_workspace"))
    )
    fun preview(sessionId: String, prompt: String, workspace: String = "") = post(
        "/api/v1/gemini-executor/sessions/$sessionId/preview",
        payload(sessionId, prompt, workspace, "gemini_patch_preview", listOf("read_workspace", "scan_workspace", "create_patch_preview"))
    )

    private fun payload(sessionId: String, prompt: String, workspace: String, operationType: String, capabilities: List<String>): String {
        val workspaceValue = if (workspace.isBlank()) "null" else JsonPayload.string(workspace)
        val caps = capabilities.joinToString(",") { JsonPayload.string(it) }
        return "{" +
            "\"session_id\":${JsonPayload.string(sessionId)}," +
            "\"prompt\":${JsonPayload.string(prompt)}," +
            "\"workspace_context\":$workspaceValue," +
            "\"operation_type\":${JsonPayload.string(operationType)}," +
            "\"requested_capabilities\":[$caps]" +
            "}"
    }
}
