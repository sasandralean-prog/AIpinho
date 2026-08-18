package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonConnectionProfileCard(context: Context, name: String, host: String, ports: String) : NeonCyberCard(context, name, host) {
    init { addBody(ports) }
}
