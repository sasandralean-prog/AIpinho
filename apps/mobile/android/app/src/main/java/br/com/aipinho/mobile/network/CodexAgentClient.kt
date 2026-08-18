package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.ui.policies.ChatAutoRefreshPolicy
import br.com.aipinho.mobile.utils.Redaction
import br.com.aipinho.mobile.utils.SafeUrlBuilder
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

class CodexAgentClient(
    private val profileRef: ConnectionProfile,
    private val tokenRef: () -> String?,
) : BaseApiClient(profileRef, profileRef.corePort, tokenRef, ChatAutoRefreshPolicy.chatRequestTimeoutMs) {
    fun health() = get("/api/v1/codex-agent/health")
    fun configStatus() = get("/api/v1/codex-agent/config/status")
    fun sessions() = get("/api/v1/codex-agent/sessions")
    fun createSession() = post("/api/v1/codex-agent/sessions", "{\"title\":\"Codex Agent\"}")
    fun renameSession(sessionId: String, title: String) = post("/api/v1/codex-agent/sessions/$sessionId/rename", "{\"title\":${JsonPayload.string(title)}}")
    fun deleteSession(sessionId: String) = delete("/api/v1/codex-agent/sessions/$sessionId")
    fun messages(sessionId: String) = get("/api/v1/codex-agent/sessions/$sessionId/messages")
    fun send(
        sessionId: String,
        prompt: String,
        workspace: String = "",
        autorun: Boolean = true,
        autoreview: Boolean = true,
        autoapproval: Boolean = true,
    ) = post(
        "/api/v1/codex-agent/sessions/$sessionId/send",
        payload(sessionId, prompt, workspace, "codex_chat", emptyList(), autorun, autoreview, autoapproval)
    )
    fun plan(sessionId: String, prompt: String, workspace: String = "") = post(
        "/api/v1/codex-agent/sessions/$sessionId/plan",
        payload(sessionId, prompt, workspace, "codex_plan", if (workspace.isBlank()) emptyList() else listOf("read_workspace", "scan_workspace"), true, true, true)
    )
    fun preview(sessionId: String, prompt: String, workspace: String = "") = post(
        "/api/v1/codex-agent/sessions/$sessionId/preview",
        payload(sessionId, prompt, workspace, "codex_patch_preview", listOf("read_workspace", "scan_workspace", "create_patch_preview"), true, true, true)
    )
    fun viewModel(sessionId: String, afterEventId: String? = null): ApiResponse {
        val suffix = afterEventId?.takeIf { it.isNotBlank() }?.let { "&after_event_id=${encode(it)}" }.orEmpty()
        return get("/api/v1/mobile/codex/view-model?session_id=${encode(sessionId)}$suffix")
    }
    fun runEvents(runId: String, afterEventId: String? = null): ApiResponse {
        val suffix = afterEventId?.takeIf { it.isNotBlank() }?.let { "?after_event_id=${encode(it)}" }.orEmpty()
        return get("/api/v1/codex-agent/runs/$runId/events$suffix")
    }
    fun cancelRun(runId: String) = post("/api/v1/codex-agent/runs/$runId/cancel")
    fun artifacts(sessionId: String) = get("/api/v1/codex-agent/sessions/$sessionId/artifacts")
    fun codexArtifactDownloadPath(artifactId: String) = "/api/v1/codex-agent/artifacts/$artifactId/download"

    fun uploadArtifact(sessionId: String, filename: String, bytes: ByteArray, contentType: String, runId: String? = null): ApiResponse {
        val boundary = "AIpinhoCodex${UUID.randomUUID().toString().replace("-", "")}"
        val path = buildString {
            append("/api/v1/codex-agent/sessions/")
            append(sessionId)
            append("/artifacts/upload")
            if (!runId.isNullOrBlank()) append("?run_id=").append(encode(runId))
        }
        val urlText = SafeUrlBuilder.build(profileRef.host, profileRef.corePort, path)
        return try {
            val head = "--$boundary\r\n" +
                "Content-Disposition: form-data; name=\"file\"; filename=\"${filename.replace("\"", "_")}\"\r\n" +
                "Content-Type: $contentType\r\n\r\n"
            val tail = "\r\n--$boundary--\r\n"
            val body = head.toByteArray(Charsets.UTF_8) + bytes + tail.toByteArray(Charsets.UTF_8)
            val connection = (URL(urlText).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = ChatAutoRefreshPolicy.chatRequestTimeoutMs
                readTimeout = ChatAutoRefreshPolicy.chatRequestTimeoutMs
                setRequestProperty("Accept", "application/json; charset=utf-8")
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
                tokenRef()?.takeIf { it.isNotBlank() }?.let { setRequestProperty("Authorization", "Bearer $it") }
                doOutput = true
                outputStream.use { it.write(body) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            ApiResponse(code in 200..299, code, Redaction.redact(text), if (code in 200..299) null else Redaction.redact(text))
        } catch (error: Exception) {
            ApiResponse(false, 0, "", Redaction.redact(error.message.orEmpty()))
        }
    }

    private fun payload(
        sessionId: String,
        prompt: String,
        workspace: String,
        operationType: String,
        capabilities: List<String>,
        autorun: Boolean,
        autoreview: Boolean,
        autoapproval: Boolean,
    ): String {
        val workspaceValue = if (workspace.isBlank()) "null" else JsonPayload.string(workspace)
        val caps = capabilities.joinToString(",") { JsonPayload.string(it) }
        return "{" +
            "\"session_id\":${JsonPayload.string(sessionId)}," +
            "\"prompt\":${JsonPayload.string(prompt)}," +
            "\"workspace_context\":$workspaceValue," +
            "\"operation_type\":${JsonPayload.string(operationType)}," +
            "\"requested_capabilities\":[$caps]," +
            "\"autorun_enabled\":$autorun," +
            "\"autoreview_enabled\":$autoreview," +
            "\"autoapproval_enabled\":$autoapproval" +
            "}"
    }

    private fun encode(value: String) = java.net.URLEncoder.encode(value, "UTF-8")
}
