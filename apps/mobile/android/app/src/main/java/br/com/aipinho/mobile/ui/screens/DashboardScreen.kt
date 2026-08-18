package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.network.BootstrapControlClient
import br.com.aipinho.mobile.network.MonitorClient
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.utils.MobileUiAsync
import org.json.JSONArray
import org.json.JSONObject

class DashboardScreen {
    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        val mobileViewModels = MobileViewModelClient(profile) { tokens.load() }
        val monitor = MonitorClient(profile) { tokens.load() }
        val bootstrap = BootstrapControlClient(profile) { tokens.load() }
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val cockpit = HumanizedViewModelTerminal(context, "Dashboard cockpit", minHeightDp = 420)
        val backendStatusCard = NeonCyberCard(context, "Backend", "Fonte oficial: /api/v1/mobile/view-model/dashboard").apply {
            val statusText = addBody("Verificando estado do backend...")
            addView(NeonActionGroup(context, listOf(
                NeonButton(context, "Atualizar") {
                    MobileUiAsync.run(context, { statusText.text = it }) {
                        fetchOfficialBackendStatus(mobileViewModels)
                    }
                },
                NeonButton(context, "Reiniciar backend") {
                    statusText.text = "Reiniciando backend pelos scripts canonicos..."
                    MobileUiAsync.run(context, { statusText.text = it }) {
                        val restart = monitor.restartBackend()
                        "${renderRestartResult(restart.body, restart.statusCode)}\n\n${fetchOfficialBackendStatus(mobileViewModels)}"
                    }
                },
                NeonButton(context, "Reiniciar monitor 9099") {
                    statusText.text = "Reiniciando monitor 9099 pelo bootstrap 9080..."
                    MobileUiAsync.run(context, { statusText.text = it }) {
                        val restart = bootstrap.restartMonitor()
                        "${renderRestartResult(restart.body, restart.statusCode)}\n\n${fetchOfficialBackendStatus(mobileViewModels)}"
                    }
                },
            )))
            MobileUiAsync.run(context, { statusText.text = it }) {
                fetchOfficialBackendStatus(mobileViewModels)
            }
        }

        root.addView(NeonSectionHeader(context, "Dashboard"))
        root.addView(backendStatusCard)
        root.addView(NeonCyberCard(context, "Fonte oficial", "/api/v1/mobile/view-model/dashboard").apply {
            addBody("A tela renderiza cards humanizados do backend. Policy, safety e final status nao sao decididos pela UI.")
        })
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Atualizar cockpit") {
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val response = mobileViewModels.dashboard()
                    response.body.ifBlank { "dashboard_view_model_unavailable status=${response.statusCode}" }
                }
            },
            NeonButton(context, "Status VM") {
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val response = mobileViewModels.status()
                    response.body.ifBlank { "mobile_view_model_status_unavailable status=${response.statusCode}" }
                }
            },
        )))
        root.addView(cockpit)

        MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
            val response = mobileViewModels.status()
            response.body.ifBlank { "mobile_view_model_status_unavailable status=${response.statusCode}" }
        }
        return MobileScreenScaffold(context, root)
    }

    private fun fetchOfficialBackendStatus(mobileViewModels: MobileViewModelClient): String {
        val dashboard = mobileViewModels.dashboard()
        if (dashboard.ok && dashboard.body.isNotBlank()) {
            return renderBackendStatus(dashboard.body)
        }
        val status = mobileViewModels.status()
        return renderCoreStatusFallback(status.body, dashboard.statusCode, status.statusCode, dashboard.error)
    }

    private fun renderBackendStatus(payload: String): String {
        return runCatching {
            val root = JSONObject(payload)
            val cards = root.optJSONArray("cards")
            val state = root.optJSONObject("state")
            val core = findCard(cards, "dashboard_core_backend")
            val control = findCard(cards, "dashboard_backend_control")
            val coreStatus = core?.optString("status")?.takeIf { it.isNotBlank() }
                ?: state?.optString("status")?.takeIf { it.isNotBlank() }
                ?: root.optString("status", "unknown")
            val dashboardStatus = state?.optString("status", "unknown") ?: "unknown"
            val coreMessage = answer(core, "what_is_happening")
                ?: "Core Backend consultado pela fonte oficial do mobile."
            val controlStatus = control?.optJSONObject("metadata")?.optString("status", "unknown") ?: "unknown"
            val backendPort = control?.optJSONObject("metadata")?.optString("backend_port")?.takeIf { it.isNotBlank() }
                ?: "nao informado"
            val bootstrapPort = control?.optJSONObject("metadata")?.optString("bootstrap_port")?.takeIf { it.isNotBlank() }
                ?: "nao informado"
            val monitorPort = control?.optJSONObject("metadata")?.optString("control_port")?.takeIf { it.isNotBlank() }
                ?: "nao informado"
            val monitorStatus = control?.optJSONObject("metadata")?.optString("monitor_status", "unknown")
                ?: controlStatus
            val warnings = state?.optJSONArray("warnings").toLines(limit = 4)
            buildString {
                append("Status: ${humanStatus(coreStatus)}\n")
                append(coreMessage)
                if (dashboardStatus !in setOf("healthy", "ok", "online")) {
                    append("\nObservabilidade: ${humanStatus(dashboardStatus)}")
                }
                if (warnings.isNotEmpty()) {
                    append("\nAvisos:\n")
                    append(warnings.joinToString("\n") { "- $it" })
                }
                append("\nCore: $backendPort")
                append("\nBootstrap: $bootstrapPort")
                append("\nMonitor: $monitorPort (${humanStatus(monitorStatus)})")
            }
        }.getOrElse {
            "Status: Desconhecido\nNao consegui interpretar o dashboard oficial. O core sera consultado no fallback."
        }
    }

    private fun renderCoreStatusFallback(payload: String, dashboardStatusCode: Int, statusStatusCode: Int, dashboardError: String?): String {
        return runCatching {
            val root = JSONObject(payload)
            val status = root.optString("status", "unknown")
            val label = if (status in setOf("ok", "healthy", "online")) "Online" else humanStatus(status)
            val inventory = root.optJSONObject("endpoint_inventory")
            val inventoryStatus = inventory?.optString("status", "")?.takeIf { it.isNotBlank() }
            buildString {
                append("Status: $label\n")
                append("Core /api/v1 respondeu; o dashboard oficial falhou com HTTP $dashboardStatusCode.")
                dashboardError?.takeIf { it.isNotBlank() }?.let {
                    append("\nCausa sanitizada: $it")
                }
                if (inventoryStatus != null) {
                    append("\nInventario de endpoints: ${humanStatus(inventoryStatus)}")
                }
            }
        }.getOrElse {
            "Status: Offline\nNao consegui consultar o core pelo contrato /api/v1 (dashboard HTTP $dashboardStatusCode, status HTTP $statusStatusCode)."
        }
    }

    private fun findCard(cards: JSONArray?, cardId: String): JSONObject? {
        if (cards == null) return null
        for (index in 0 until cards.length()) {
            val card = cards.optJSONObject(index) ?: continue
            if (card.optString("card_id") == cardId) return card
        }
        return null
    }

    private fun answer(card: JSONObject?, key: String): String? {
        return card?.optJSONObject("answers")?.optString(key)?.takeIf { it.isNotBlank() }
    }

    private fun JSONArray?.toLines(limit: Int): List<String> {
        if (this == null) return emptyList()
        val lines = mutableListOf<String>()
        for (index in 0 until length()) {
            val value = optString(index)
            if (value.isNotBlank()) lines.add(value)
            if (lines.size >= limit) break
        }
        return lines
    }

    private fun humanStatus(status: String): String {
        return when (status) {
            "ok", "healthy", "online" -> "Online"
            "running", "restarting" -> "Reiniciando"
            "degraded" -> "Degradado"
            "offline", "failed" -> "Offline"
            "blocked" -> "Bloqueado"
            "pending" -> "Pendente"
            "historical" -> "Historico"
            "unknown" -> "Desconhecido"
            else -> status.ifBlank { "Desconhecido" }
        }
    }

    private fun renderRestartResult(payload: String, statusCode: Int): String {
        return runCatching {
            val root = JSONObject(payload)
            val restart = root.optJSONObject("restart")
            val status = restart?.optString("status", root.optString("status", "unknown")) ?: root.optString("status", "unknown")
            val message = restart?.optString("human_message", "") ?: ""
            "Pedido de reinicio: $status\n${message.ifBlank { "O supervisor registrou a tentativa de reinicio." }}"
        }.getOrElse {
            "Pedido de reinicio: falhou\nHTTP $statusCode"
        }
    }
}
