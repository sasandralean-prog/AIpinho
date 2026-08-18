package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.AgentTabConfig
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.ui.policies.ChatAutoRefreshPolicy
import java.net.URLEncoder

class AgentApiClient(
    profile: ConnectionProfile,
    tokenProvider: () -> String?,
    private val config: AgentTabConfig,
) : BaseApiClient(profile, profile.corePort, tokenProvider, ChatAutoRefreshPolicy.chatRequestTimeoutMs) {
    fun health() = get("${config.routePrefix}/health")

    fun configStatus() = get("${config.routePrefix}/config/status")

    fun sessions() = get("${config.routePrefix}/sessions")

    fun createSession(title: String = config.displayName) =
        post("${config.routePrefix}/sessions", "{\"title\":${JsonPayload.string(title)}}")

    fun renameSession(sessionId: String, title: String): ApiResponse {
        val path = "${config.routePrefix}/sessions/${encode(sessionId)}"
        return if (config.agentId == "lucio") {
            patch(path, "{\"title\":${JsonPayload.string(title)}}")
        } else {
            post("$path/rename", "{\"title\":${JsonPayload.string(title)}}")
        }
    }

    fun deleteSession(sessionId: String) =
        delete("${config.routePrefix}/sessions/${encode(sessionId)}")

    fun messages(sessionId: String) =
        get("${config.routePrefix}/sessions/${encode(sessionId)}/messages")

    fun send(
        sessionId: String,
        prompt: String,
        workspace: String,
        artifactIds: List<String>,
        autorun: Boolean,
        autoreview: Boolean,
        autoapproval: Boolean,
    ) = post(
        "${config.routePrefix}/sessions/${encode(sessionId)}/send",
        requestPayload(
            sessionId = sessionId,
            prompt = prompt,
            workspace = workspace,
            operationType = config.operationType,
            capabilities = emptyList(),
            artifactIds = artifactIds,
            autorun = autorun,
            autoreview = autoreview,
            autoapproval = autoapproval,
        ),
    )

    fun plan(sessionId: String, prompt: String, workspace: String) =
        post(
            "${config.routePrefix}/sessions/${encode(sessionId)}/plan",
            requestPayload(
                sessionId = sessionId,
                prompt = prompt,
                workspace = workspace,
                operationType = "${config.agentId}_plan",
                capabilities = if (workspace.isBlank()) emptyList() else listOf("read_workspace", "scan_workspace"),
            ),
        )

    fun preview(sessionId: String, prompt: String, workspace: String) =
        post(
            "${config.routePrefix}/sessions/${encode(sessionId)}/preview",
            requestPayload(
                sessionId = sessionId,
                prompt = prompt,
                workspace = workspace,
                operationType = "${config.agentId}_patch_preview",
                capabilities = listOf("read_workspace", "scan_workspace", "create_patch_preview"),
            ),
        )

    fun routePreview(sessionId: String, prompt: String, workspace: String, artifactIds: List<String>) =
        post(
            "${config.routePrefix}/sessions/${encode(sessionId)}/route-preview",
            requestPayload(
                sessionId = sessionId,
                prompt = prompt,
                workspace = workspace,
                operationType = config.operationType,
                capabilities = emptyList(),
                artifactIds = artifactIds,
            ),
        )

    fun viewModel(sessionId: String, afterEventId: String?, mode: String): ApiResponse {
        val query = buildList {
            afterEventId?.takeIf { it.isNotBlank() }?.let { add("after_event_id=${encode(it)}") }
            if (config.agentId == "lucio") add("mode=${encode(mode)}")
        }.joinToString("&")
        val suffix = query.takeIf { it.isNotBlank() }?.let { "?$it" }.orEmpty()
        return get("${config.routePrefix}/sessions/${encode(sessionId)}/view-model$suffix")
    }

    fun cancelRun(runId: String) =
        post("${config.routePrefix}/runs/${encode(runId)}/cancel")

    fun artifacts(sessionId: String) =
        get("/api/v1/artifacts/by-agent/${encode(config.agentId)}?session_id=${encode(sessionId)}")

    fun uploadTextArtifact(
        sessionId: String,
        filename: String,
        contentType: String,
        content: String,
        runId: String?,
        encoding: String = "text",
    ) = post(
        "/api/v1/agents/${encode(config.agentId)}/sessions/${encode(sessionId)}/artifacts/upload",
        "{" +
            "\"filename\":${JsonPayload.string(filename)}," +
            "\"content_type\":${JsonPayload.string(contentType)}," +
            "\"content\":${JsonPayload.string(content)}," +
            "\"encoding\":${JsonPayload.string(encoding)}," +
            "\"run_id\":${runId?.let(JsonPayload::string) ?: "null"}," +
            "\"origin\":\"mobile_upload\"" +
            "}",
    )

    private fun requestPayload(
        sessionId: String,
        prompt: String,
        workspace: String,
        operationType: String,
        capabilities: List<String>,
        artifactIds: List<String> = emptyList(),
        autorun: Boolean = true,
        autoreview: Boolean = true,
        autoapproval: Boolean = true,
    ): String {
        val caps = capabilities.joinToString(",") { JsonPayload.string(it) }
        val workspaceValue = workspace.takeIf { it.isNotBlank() }?.let(JsonPayload::string) ?: "null"
        val artifacts = artifactIds.joinToString(",") {
            "{\"artifact_id\":${JsonPayload.string(it)},\"purpose\":\"evidence\"}"
        }
        val common = mutableListOf(
            "\"session_id\":${JsonPayload.string(sessionId)}",
            "\"prompt\":${JsonPayload.string(prompt)}",
            "\"operation_type\":${JsonPayload.string(operationType)}",
            "\"requested_capabilities\":[$caps]",
        )
        when (config.agentId) {
            "lucio" -> {
                common.add("\"workspace_id\":$workspaceValue")
                common.add("\"artifacts\":[$artifacts]")
            }
            "codex_agent" -> {
                common.add("\"workspace_context\":$workspaceValue")
                common.add("\"autorun_enabled\":$autorun")
                common.add("\"autoreview_enabled\":$autoreview")
                common.add("\"autoapproval_enabled\":$autoapproval")
            }
            else -> common.add("\"workspace_context\":$workspaceValue")
        }
        return "{${common.joinToString(",")}}"
    }

    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")
}
