package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile
import java.net.URLEncoder
import org.json.JSONObject

class TaskRuntimeClient(
    profile: ConnectionProfile,
    token: () -> String?,
) : BaseApiClient(profile, profile.corePort, token, timeoutMs = 60_000) {
    fun listRuns(status: String? = null, contractType: String? = null, limit: Int = 10): ApiResponse {
        val params = mutableListOf("limit=${limit.coerceIn(1, 1000)}")
        status?.takeIf { it.isNotBlank() }?.let { params.add("status=${queryValue(it)}") }
        contractType?.takeIf { it.isNotBlank() }?.let { params.add("contract_type=${queryValue(it)}") }
        return get("/api/v1/task-runs?${params.joinToString("&")}")
    }

    fun createFromPreview(previewId: String) =
        post("/api/v1/task-runs/from-preview/${pathSegment(previewId)}")

    fun start(runId: String) =
        post("/api/v1/task-runs/${pathSegment(runId)}/start")

    fun queue() =
        get("/api/v1/task-runtime/queue")

    fun cancel(runId: String, reason: String = "mobile_user_requested") =
        post(
            "/api/v1/task-runs/${pathSegment(runId)}/cancel",
            JSONObject().put("reason", reason).toString(),
        )

    fun retryNode(runId: String, nodeId: String, reason: String = "mobile_retry_node") =
        post(
            "/api/v1/task-runs/${pathSegment(runId)}/execution-graph/nodes/${pathSegment(nodeId)}/retry",
            JSONObject().put("reason", reason).toString(),
        )

    fun cancelNode(runId: String, nodeId: String, reason: String = "mobile_cancel_node") =
        post(
            "/api/v1/task-runs/${pathSegment(runId)}/execution-graph/nodes/${pathSegment(nodeId)}/cancel",
            JSONObject().put("reason", reason).toString(),
        )

    fun planningReport(runId: String) =
        get("/api/v1/task-runs/${pathSegment(runId)}/planning/report")

    fun replanNode(runId: String, nodeId: String, reason: String = "mobile_replan_node") =
        post(
            "/api/v1/task-runs/${pathSegment(runId)}/planning/nodes/${pathSegment(nodeId)}/replan",
            JSONObject().put("reason", reason).toString(),
        )

    fun result(runId: String) =
        get("/api/v1/task-runs/${pathSegment(runId)}/result")

    fun speakerUpdates(runId: String, afterEventId: String? = null): ApiResponse {
        val cursor = afterEventId?.takeIf { it.isNotBlank() }?.let { "?after_event_id=${queryValue(it)}" }.orEmpty()
        return get("/api/v1/task-runs/${pathSegment(runId)}/speaker/updates$cursor")
    }

    private fun pathSegment(value: String): String {
        require(value.matches(Regex("[A-Za-z0-9_-]+"))) { "invalid_runtime_identifier" }
        return value
    }

    private fun queryValue(value: String): String {
        require(value.matches(Regex("[A-Za-z0-9_-]+"))) { "invalid_runtime_query" }
        return URLEncoder.encode(value, Charsets.UTF_8.name())
    }
}
