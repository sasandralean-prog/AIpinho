package br.com.aipinho.mobile.ui.screens

import android.app.Activity
import android.content.Context
import android.view.View
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import br.com.aipinho.mobile.data.ConnectionRepository
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.models.ConnectionProfileType
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.components.NeonTerminalCard
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.utils.HumanFormatting

class PairingScreen(private val settings: SettingsRepository, private val tokens: TokenRepository, private val onSaved: () -> Unit) {
    fun build(context: Context): View {
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val spinner = Spinner(context).apply {
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, ConnectionProfileType.values().map { it.name })
        }
        val host = EditText(context).apply {
            hint = "Host"
            setText("127.0.0.1")
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.mutedCyan)
        }
        val token = EditText(context).apply {
            hint = "Token Bearer pareado no PC"
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.mutedCyan)
        }
        val result = NeonTerminalCard(context, "Resultado", listOf("Aguardando teste de conexão."))
        root.addView(NeonSectionHeader(context, "Primeiro acesso / Pairing"))
        root.addView(NeonCyberCard(context, "Perfil de conexão", "ADB/Wi-Fi/Tailscale/Manual").apply {
            addBody("Token não é hardcoded e será salvo com Keystore quando possível.")
        })
        root.addView(spinner)
        root.addView(host)
        root.addView(token)
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Testar conexão") {
                result.terminal.setLines(listOf("Testando portas..."))
                val selected = spinner.selectedItemPosition
                val configuredHost = host.text.toString()
                val enteredToken = token.text.toString()
                Thread {
                    val tests = ConnectionRepository { enteredToken }.test(profile(selected, configuredHost))
                    val message = HumanFormatting.connection(tests.values.count { it.ok }, tests.size)
                    (context as? Activity)?.runOnUiThread { result.terminal.setLines(listOf(message)) }
                }.start()
            },
            NeonButton(context, "Salvar") {
                if (token.text.isBlank()) {
                    result.terminal.setLines(listOf("Token obrigatório"), error = true)
                } else {
                    val profile = profile(spinner.selectedItemPosition, host.text.toString())
                    settings.saveProfile(profile)
                    tokens.save(token.text.toString())
                    onSaved()
                }
            },
        )))
        root.addView(result)
        return MobileScreenScaffold(context, root)
    }

    private fun profile(position: Int, host: String): ConnectionProfile = when (ConnectionProfileType.values()[position]) {
        ConnectionProfileType.ADB_REVERSE -> ConnectionProfile.adbReverse()
        ConnectionProfileType.WIFI_LAN -> ConnectionProfile.wifi(host)
        ConnectionProfileType.TAILSCALE -> ConnectionProfile.tailscale(host)
        ConnectionProfileType.MANUAL -> ConnectionProfile.manual(host, 9088, 9089, 9098, 9099, 9080)
    }
}
