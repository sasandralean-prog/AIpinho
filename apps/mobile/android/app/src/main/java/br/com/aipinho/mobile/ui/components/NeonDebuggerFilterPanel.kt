package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout

class NeonDebuggerFilterPanel(context: Context, selected: String, onSelect: (String) -> Unit) : LinearLayout(context) {
    val filters = listOf("events", "policy", "context", "rag", "memory", "skill", "maintenance", "model", "validation", "patch", "artifact", "supervisor", "mobile_sync", "speaker", "raw_sanitized")
    init {
        orientation = HORIZONTAL
        filters.forEach { addView(NeonFilterChip(context, it, selected == it) { onSelect(it) }) }
    }
}
