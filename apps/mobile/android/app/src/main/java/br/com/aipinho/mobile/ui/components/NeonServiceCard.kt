package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonServiceCard(context: Context, name: String, status: String, detail: String) : NeonCyberCard(context, name, status) {
    init { addBody(detail, error = status.contains("down", true)) }
}
