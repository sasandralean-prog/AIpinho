package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import br.com.aipinho.mobile.models.AgentTabConfig

class GeminiExecutorScreen {
    fun build(context: Context): View = AgentTabScreen(
        AgentTabConfig(
            agentId = "gemini_executor",
            displayName = "Gemini",
            routePrefix = "/api/v1/gemini-executor",
            operationType = "gemini_chat",
            providerLabel = "Gemini Cloud | Executor",
            externalProviderNotice = "Provider externo. Chaves permanecem somente no backend.",
        )
    ).build(context)
}
