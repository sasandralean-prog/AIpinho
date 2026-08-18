package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile

class GovernanceClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.corePort, token, timeoutMs = 30_000) {
    fun health() = get("/api/v1/config/health")
    fun effectivePolicy() = get("/api/v1/config/effective-policy")
    fun workspaces() = get("/api/v1/config/workspaces")
    fun permissionMatrix() = get("/api/v1/config/permission-matrix")
    fun changes() = get("/api/v1/config/changes")
    fun backups() = get("/api/v1/config/backups")
    fun flowRules() = get("/api/v1/workspace-flows/rules")
    fun createWorkspace(workspaceId: String, label: String, rootPath: String, role: String, permissionsJson: String) = post(
        "/api/v1/config/workspaces",
        """
        {
          "workspace_id":"${escapeJson(workspaceId)}",
          "root_path":"${escapeJson(rootPath)}",
          "role":"${escapeJson(role)}",
          "human_label":"${escapeJson(label)}",
          "reason":"mobile_governance_console_workspace_change",
          "approval_required":true,
          "enabled":true,
          "permissions":${permissionsJson.ifBlank { "{}" }},
          "evidence":["mobile_governance_console"]
        }
        """.trimIndent()
    )
    fun approveChange(changeId: String) = post("/api/v1/config/changes/${escapePath(changeId)}/approve")
    fun applyChange(changeId: String) = post("/api/v1/config/changes/${escapePath(changeId)}/apply")
    fun rollback(backupId: String) = post("/api/v1/config/rollback/${escapePath(backupId)}")
    fun flowPlan(operation: String, sourceWorkspaceId: String, targetWorkspaceId: String) = post(
        "/api/v1/workspace-flows/plan",
        """
        {
          "operation":"${escapeJson(operation)}",
          "source":{"workspace_id":"${escapeJson(sourceWorkspaceId)}","path":""},
          "target":{"workspace_id":"${escapeJson(targetWorkspaceId)}","path":""},
          "requested_by":{"type":"user","id":"mobile"}
        }
        """.trimIndent()
    )

    private fun escapeJson(value: String): String =
        value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r")

    private fun escapePath(value: String): String = java.net.URLEncoder.encode(value, Charsets.UTF_8.name())
}
