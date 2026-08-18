package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import br.com.aipinho.mobile.models.AgentTabConfig

class CodexAgentScreen {
    fun build(context: Context): View = AgentTabScreen(
        AgentTabConfig(
            agentId = "codex_agent",
            displayName = "Codex",
            routePrefix = "/api/v1/codex-agent",
            operationType = "codex_chat",
            providerLabel = "Codex CLI | Executor",
        )
    ).build(context)
}
