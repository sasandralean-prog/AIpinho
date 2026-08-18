package br.com.aipinho.mobile.data

import android.content.Context

class ChatSessionRepository(context: Context) {
    private val prefs = context.getSharedPreferences("aipinho_chat", Context.MODE_PRIVATE)

    fun saveActiveSessionId(sessionId: String?) {
        prefs.edit().putString("active_session_id", sessionId.orEmpty()).apply()
    }

    fun loadActiveSessionId(): String? {
        return prefs.getString("active_session_id", null)?.takeIf { it.isNotBlank() }
    }

    fun saveDraft(value: String) {
        prefs.edit().putString("draft", value).apply()
    }

    fun loadDraft(): String = prefs.getString("draft", "") ?: ""

    fun clearDraft() {
        prefs.edit().remove("draft").apply()
    }

    fun saveLastConversation(value: String) {
        prefs.edit().putString("last_conversation", value).apply()
    }

    fun loadLastConversation(): String = prefs.getString("last_conversation", "") ?: ""

    fun saveLastOperationalResult(value: String) {
        prefs.edit().putString("last_operational_result", value).apply()
    }

    fun loadLastOperationalResult(): String {
        return prefs.getString("last_operational_result", "") ?: ""
    }

    fun saveActiveTaskRunId(runId: String?) {
        prefs.edit().putString("active_task_run_id", runId.orEmpty()).apply()
    }

    fun loadActiveTaskRunId(): String? {
        return prefs.getString("active_task_run_id", null)?.takeIf { it.isNotBlank() }
    }

    fun saveLatestArtifact(artifactId: String?, filename: String?, contentType: String?) {
        prefs.edit()
            .putString("latest_artifact_id", artifactId.orEmpty())
            .putString("latest_artifact_filename", filename.orEmpty())
            .putString("latest_artifact_content_type", contentType.orEmpty())
            .apply()
    }

    fun loadLatestArtifactId(): String? {
        return prefs.getString("latest_artifact_id", null)?.takeIf { it.isNotBlank() }
    }

    fun loadLatestArtifactFilename(): String? {
        return prefs.getString("latest_artifact_filename", null)?.takeIf { it.isNotBlank() }
    }

    fun loadLatestArtifactContentType(): String? {
        return prefs.getString("latest_artifact_content_type", null)?.takeIf { it.isNotBlank() }
    }
}
