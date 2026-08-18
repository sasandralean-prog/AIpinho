package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import br.com.aipinho.mobile.models.AgentTabConfig

class LucioAgentScreen {
    fun build(context: Context): View = AgentTabScreen(
        AgentTabConfig(
            agentId = "lucio",
            displayName = "Lucio",
            routePrefix = "/api/v1/lucio-agent",
            operationType = "lucio_chat",
            providerLabel = "OpenAI | Estrategico",
            supportsRoutePreview = true,
            supportsPlan = false,
            supportsPreview = false,
            externalProviderNotice = "Agente estrategico multimodal. Execucao local e delegada pelos gates.",
        )
    ).build(context)
}
