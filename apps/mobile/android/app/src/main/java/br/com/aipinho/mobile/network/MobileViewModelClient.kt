package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile

class MobileViewModelClient(profile: ConnectionProfile, token: () -> String?) : BaseApiClient(profile, profile.corePort, token, timeoutMs = MobileViewModelTimeoutPolicy.defaultTimeoutMs) {
    fun status() = get("/api/v1/mobile/view-model/status")
    fun dashboard() = get("/api/v1/mobile/view-model/dashboard")
    fun agents() = get("/api/v1/mobile/view-model/agents")
    fun chat(sessionId: String) = get("/api/v1/mobile/view-model/chat/$sessionId")
    fun pipeline() = get("/api/v1/mobile/view-model/pipeline")
    fun pipeline(taskId: String) = get("/api/v1/mobile/view-model/pipeline/$taskId")
    fun debugger() = get("/api/v1/mobile/view-model/debugger")
    fun debuggerTrace(traceId: String) = get("/api/v1/mobile/view-model/debugger/trace/$traceId")
    fun config() = get("/api/v1/mobile/view-model/config")
    fun universalApprovers() = get("/api/v1/universal-approvers/mobile-view")
    fun refresh() = post("/api/v1/mobile/view-model/refresh")
    fun copy(cardId: String) = post("/api/v1/mobile/view-model/cards/$cardId/copy")
    fun rawCopy(rawRef: String) = post("/api/v1/mobile/view-model/raw/$rawRef/copy")
}

object MobileViewModelTimeoutPolicy {
    const val defaultTimeoutMs: Int = 30_000
}
