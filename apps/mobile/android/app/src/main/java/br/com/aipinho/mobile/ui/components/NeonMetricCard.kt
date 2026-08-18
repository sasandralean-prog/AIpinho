package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonMetricCard(context: Context, label: String, value: String) : NeonCyberCard(context, label) {
    init { addBody(value) }
}
