package br.com.aipinho.mobile.models

data class AgentTabConfig(
    val agentId: String,
    val displayName: String,
    val routePrefix: String,
    val operationType: String,
    val providerLabel: String,
    val supportsRoutePreview: Boolean = false,
    val supportsPlan: Boolean = true,
    val supportsPreview: Boolean = true,
    val supportsWorkspace: Boolean = true,
    val externalProviderNotice: String? = null,
)

data class AgentMobileState(
    val selectedSessionByAgent: MutableMap<String, String> = mutableMapOf(),
    val latestEventBySession: MutableMap<String, String> = mutableMapOf(),
    val activeRunBySession: MutableMap<String, String> = mutableMapOf(),
    val attachedArtifactIdsBySession: MutableMap<String, MutableList<String>> = mutableMapOf(),
)
