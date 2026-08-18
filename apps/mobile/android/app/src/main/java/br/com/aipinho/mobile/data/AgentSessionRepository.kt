package br.com.aipinho.mobile.data

import android.content.Context

class AgentSessionRepository(context: Context) {
    private val prefs = context.getSharedPreferences("aipinho_agent_sessions", Context.MODE_PRIVATE)

    fun saveSelectedSession(agentId: String, sessionId: String?) {
        prefs.edit().putString(key(agentId), sessionId.orEmpty()).apply()
    }

    fun loadSelectedSession(agentId: String): String? =
        prefs.getString(key(agentId), null)?.takeIf { it.isNotBlank() }

    private fun key(agentId: String) = "selected_session_${agentId.lowercase()}"
}
