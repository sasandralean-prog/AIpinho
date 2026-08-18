package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.view.View
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.models.DebuggerFilterState
import br.com.aipinho.mobile.network.MobileEvidenceClient
import br.com.aipinho.mobile.network.MobileSupportBundleClient
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonSearchField
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.utils.MobileUiAsync

class DebuggerScreen {
    companion object { private var filter = DebuggerFilterState() }

    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        val mobileViewModels = MobileViewModelClient(profile) { tokens.load() }
        val evidence = MobileEvidenceClient(profile) { tokens.load() }
        val supportBundle = MobileSupportBundleClient(profile) { tokens.load() }
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val query = NeonSearchField(context, "trace_id / evidence ref / task_id").apply { setText(filter.query) }
        val cockpit = HumanizedViewModelTerminal(context, "Debugger cockpit", minHeightDp = 460)

        root.addView(NeonSectionHeader(context, "Debugger 2.0"))
        root.addView(NeonCyberCard(context, "Fonte oficial", "/api/v1/mobile/view-model/debugger").apply {
            addBody("Eventos, timeline, evidence, raw_ref e diagnostics aparecem sanitizados e filtraveis.")
        })
        root.addView(query)
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Debugger") {
                filter = filter.copy(query = query.text.toString())
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val response = mobileViewModels.debugger()
                    response.body.ifBlank { "debugger_view_model_unavailable status=${response.statusCode}" }
                }
            },
            NeonButton(context, "Trace") {
                filter = filter.copy(query = query.text.toString())
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val traceId = filter.query.ifBlank { "latest" }
                    val response = mobileViewModels.debuggerTrace(traceId)
                    response.body.ifBlank { "debugger_trace_view_model_unavailable status=${response.statusCode}" }
                }
            },
            NeonButton(context, "Evidence") {
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val ref = query.text.toString().ifBlank { "latest" }
                    val response = evidence.evidence("event", ref)
                    response.body.ifBlank { "evidence_view_model_unavailable status=${response.statusCode}" }
                }
            },
            NeonButton(context, "Support") {
                MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
                    val response = supportBundle.preview()
                    response.body.ifBlank { "support_bundle_preview_unavailable status=${response.statusCode}" }
                }
            },
        )))
        root.addView(cockpit)

        MobileUiAsync.run(context, { cockpit.setPayload(it) }) {
            val response = mobileViewModels.debugger()
            response.body.ifBlank { "debugger_view_model_unavailable status=${response.statusCode}" }
        }
        return MobileScreenScaffold(context, root)
    }
}
