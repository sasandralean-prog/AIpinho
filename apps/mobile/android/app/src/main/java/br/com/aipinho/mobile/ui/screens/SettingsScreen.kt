package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import br.com.aipinho.mobile.AppConfig
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.ThemePreferenceRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.models.ConnectionProfileType
import br.com.aipinho.mobile.network.ConnectionClient
import br.com.aipinho.mobile.network.GovernanceClient
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.ui.cards.ConfigCapabilityCard
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonConnectionAutoFillPanel
import br.com.aipinho.mobile.ui.components.NeonConnectionProfileCard
import br.com.aipinho.mobile.ui.components.NeonCopyButton
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.components.NeonTerminalCard
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.utils.MobileUiAsync
import org.json.JSONObject

class SettingsScreen(private val settings: SettingsRepository, private val tokens: TokenRepository) {
    fun build(context: Context): View {
        val theme = ThemePreferenceRepository(context)
        val profile = settings.loadProfile()
        val client = ConnectionClient(profile) { tokens.load() }
        val mobileViewModels = MobileViewModelClient(profile) { tokens.load() }
        val governance = GovernanceClient(profile) { tokens.load() }
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val hostInput = EditText(context).apply {
            setText(profile.host)
            hint = "Host"
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan)
        }
        val output = NeonTerminalCard(context, "Connection Doctor", listOf("Testa portas, token, SSE e artifact por contrato."))
        val humanized = ConfigCapabilityCard(context)
        val viewModelTerminal = HumanizedViewModelTerminal(context, "Config cockpit", minHeightDp = 340)
        val governanceTerminal = NeonTerminalCard(context, "Governance console", listOf("Use os botoes para consultar policy, workspaces, matrix, backups e flow rules."), minHeightDp = 280)
        var lastChangeId: String? = null
        var lastBackupId: String? = null
        fun governanceInput(value: String) = EditText(context).apply {
            setText(value)
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan)
        }
        val workspaceIdInput = governanceInput("workspace_id")
        val workspaceLabelInput = governanceInput("label")
        val workspacePathInput = governanceInput("root_path")
        val workspaceRoleInput = governanceInput("target_mutable")
        val permissionsInput = governanceInput("""{"read_file":"allowed","list_files":"allowed","create_file":"ask","modify_file":"ask"}""")
        root.addView(NeonSectionHeader(context, "Configurações"))
        root.addView(humanized)
        root.addView(viewModelTerminal)
        root.addView(NeonCyberCard(context, "Token", tokens.preview()).apply {
            addBody("Token salvo via Keystore quando possível e sempre redigido na UI.")
        })
        root.addView(hostInput)
        root.addView(NeonConnectionAutoFillPanel(context, "policy", profile.host, "9088/9089/9098/9099"))
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "ADB") {
                settings.saveProfile(ConnectionProfile.adbReverse())
                output.terminal.setLines(listOf("ADB Reverse selecionado", "host=127.0.0.1"))
            },
            NeonButton(context, "Wi-Fi") {
                settings.saveProfile(ConnectionProfile.wifi(hostInput.text.toString().ifBlank { profile.host }))
                output.terminal.setLines(listOf("Wi-Fi selecionado", "host=${hostInput.text}"))
            },
            NeonButton(context, "Tailscale") {
                settings.saveProfile(ConnectionProfile.tailscale(hostInput.text.toString().ifBlank { profile.host }))
                output.terminal.setLines(listOf("Tailscale selecionado", "host=${hostInput.text}"))
            },
            NeonButton(context, "Manual") {
                settings.saveProfile(ConnectionProfile(ConnectionProfileType.MANUAL, hostInput.text.toString().ifBlank { profile.host }))
                output.terminal.setLines(listOf("Manual selecionado", "portas editáveis em sprint futuro"))
            },
        )))
        root.addView(NeonConnectionProfileCard(context, profile.type.name, profile.host, "core=${profile.corePort} realtime=${profile.realtimePort} artifacts=${profile.artifactPort} monitor=${profile.monitorPort}"))
        root.addView(NeonActionGroup(context, listOf(
            NeonCopyButton(context, "Copiar ADB") { AppConfig.adbCommands.joinToString("\n") },
            NeonButton(context, "Sugestões") {
                MobileUiAsync.run(context, { output.terminal.setLines(it.lines()) }) { client.suggestions().body }
            },
            NeonButton(context, "Testar conexão") {
                MobileUiAsync.run(context, { output.terminal.setLines(it.lines()) }) { client.profiles().body }
            },
        )))
        root.addView(NeonCyberCard(context, "Modos", "Compact / Neon Reduced / Support Bundle").apply {
            addBody("Neon reduced: ${theme.neonReduced()}\nSupport Bundle: preview sanitizado; artifact_id quando backend suportar.")
        })
        root.addView(NeonCyberCard(context, "Governanca", "ConfigChangeRequest -> preview -> approval -> apply").apply {
            addBody("A UI consulta e solicita fluxos pelo backend. Nenhuma config e editada direto pelo app.")
        })
        root.addView(workspaceIdInput)
        root.addView(workspaceLabelInput)
        root.addView(workspacePathInput)
        root.addView(workspaceRoleInput)
        root.addView(permissionsInput)
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Policy") {
                MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.effectivePolicy().body }
            },
            NeonButton(context, "Workspaces") {
                MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.workspaces().body }
            },
            NeonButton(context, "Matrix") {
                MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.permissionMatrix().body }
            },
            NeonButton(context, "Flows") {
                MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.flowRules().body }
            },
            NeonButton(context, "Mudancas") {
                MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.changes().body }
            },
            NeonButton(context, "Backups") {
                MobileUiAsync.run(context, {
                    lastBackupId = latestBackupId(it)
                    governanceTerminal.terminal.setLines(it.lines())
                }) { governance.backups().body }
            },
            NeonButton(context, "Criar workspace") {
                MobileUiAsync.run(context, {
                    lastChangeId = changeIdFromPayload(it)
                    governanceTerminal.terminal.setLines(it.lines())
                }) {
                    governance.createWorkspace(
                        workspaceIdInput.text.toString(),
                        workspaceLabelInput.text.toString(),
                        workspacePathInput.text.toString(),
                        workspaceRoleInput.text.toString(),
                        permissionsInput.text.toString(),
                    ).body
                }
            },
            NeonButton(context, "Aprovar") {
                val id = lastChangeId
                if (id.isNullOrBlank()) governanceTerminal.terminal.setLines(listOf("Nenhuma mudanca selecionada."))
                else MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.approveChange(id).body }
            },
            NeonButton(context, "Aplicar") {
                val id = lastChangeId
                if (id.isNullOrBlank()) governanceTerminal.terminal.setLines(listOf("Nenhuma mudanca selecionada."))
                else MobileUiAsync.run(context, {
                    lastBackupId = backupIdFromPayload(it)
                    governanceTerminal.terminal.setLines(it.lines())
                }) { governance.applyChange(id).body }
            },
            NeonButton(context, "Rollback") {
                val id = lastBackupId
                if (id.isNullOrBlank()) governanceTerminal.terminal.setLines(listOf("Nenhum backup selecionado."))
                else MobileUiAsync.run(context, { governanceTerminal.terminal.setLines(it.lines()) }) { governance.rollback(id).body }
            },
        )))
        root.addView(governanceTerminal)
        root.addView(output)
        MobileUiAsync.run(context, { humanized.updateFromJson(it) }) {
            val response = mobileViewModels.config()
            response.body.ifBlank { "config_view_model_unavailable status=${response.statusCode}" }
        }
        MobileUiAsync.run(context, { viewModelTerminal.setPayload(it) }) {
            val response = mobileViewModels.config()
            response.body.ifBlank { "config_view_model_unavailable status=${response.statusCode}" }
        }
        return MobileScreenScaffold(context, root)
    }

    private fun changeIdFromPayload(payload: String): String? = try {
        JSONObject(payload).optJSONObject("change")?.optString("change_id")?.takeIf { it.isNotBlank() }
    } catch (_: Exception) {
        null
    }

    private fun backupIdFromPayload(payload: String): String? = try {
        JSONObject(payload).optJSONObject("result")?.optString("backup_id")?.takeIf { it.isNotBlank() }
    } catch (_: Exception) {
        null
    }

    private fun latestBackupId(payload: String): String? = try {
        val backups = JSONObject(payload).optJSONArray("backups")
        backups?.optJSONObject(0)?.optString("backup_id")?.takeIf { it.isNotBlank() }
    } catch (_: Exception) {
        null
    }
}
