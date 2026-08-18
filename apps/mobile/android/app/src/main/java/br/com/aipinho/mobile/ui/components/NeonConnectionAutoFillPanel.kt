package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonConnectionAutoFillPanel(context: Context, source: String, host: String, ports: String) : NeonCyberCard(context, "Auto-fill de conexão", source) {
    init { addBody("host=$host\nports=$ports\nscan_agressivo=false") }
}
