package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.utils.MobileUiAsync

class UniversalApproversScreen {
    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        val client = MobileViewModelClient(profile) { tokens.load() }
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val terminal = HumanizedViewModelTerminal(context, "Universal Approvers", minHeightDp = 520)

        fun refresh() {
            MobileUiAsync.run(context, { terminal.setPayload(it) }) {
                val response = client.universalApprovers()
                response.body.ifBlank {
                    """{"status":"failed","human_summary":"Universal Approvers indisponivel (${response.statusCode})."}"""
                }
            }
        }

        root.addView(NeonSectionHeader(context, "Universal Approvers"))
        root.addView(NeonCyberCard(context, "Authority", "AIpinho").apply {
            addBody("Participantes humanos e externos aprovam por contrato. A execucao continua sempre no runtime governado da AIpinho.")
        })
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Atualizar") { refresh() },
        )))
        root.addView(terminal)
        refresh()
        return MobileScreenScaffold(context, root)
    }
}
