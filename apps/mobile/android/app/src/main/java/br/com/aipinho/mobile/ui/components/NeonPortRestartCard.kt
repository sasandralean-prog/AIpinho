package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout

class NeonPortRestartCard(context: Context, port: Int, label: String, allowed: Boolean, onRestart: (() -> Unit)? = null) : NeonCyberCard(context, "$label:$port") {
    init {
        addBody(if (allowed) "Restart controlado via 9099." else "Restart bloqueado por política.")
        addView(NeonButton(context, if (allowed) "Reiniciar $port" else "9099 bloqueada", selected = false) {
            if (allowed) onRestart?.invoke()
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT))
    }
}
