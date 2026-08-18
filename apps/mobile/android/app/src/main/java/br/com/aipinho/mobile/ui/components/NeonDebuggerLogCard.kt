package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonDebuggerLogCard(context: Context, eventType: String, severity: String, summary: String, raw: String = "") : NeonCyberCard(context, eventType, severity) {
    init {
        addBody(summary, error = severity in setOf("error", "critical"))
        addView(NeonCopyButton(context, "Copiar evento") { "$eventType\n$severity\n$summary" })
        if (raw.isNotBlank()) addView(NeonRawCopyButton(context) { raw })
    }
}
