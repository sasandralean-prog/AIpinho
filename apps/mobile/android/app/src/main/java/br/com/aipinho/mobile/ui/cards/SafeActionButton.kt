package br.com.aipinho.mobile.ui.cards

import android.content.Context
import br.com.aipinho.mobile.ui.components.NeonButton

class SafeActionButton(context: Context, label: String, enabledByPolicy: Boolean, disabledReason: String?, onClick: (() -> Unit)? = null) : NeonButton(context, label, selected = false, onClick = onClick) {
    init {
        isEnabled = enabledByPolicy
        contentDescription = disabledReason ?: "Safe action from backend view-model"
    }
}

