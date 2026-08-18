package br.com.aipinho.mobile.ui.cards

import android.content.Context
import br.com.aipinho.mobile.ui.components.NeonButton

class RawViewerButton(context: Context, rawRef: String, onClick: (() -> Unit)? = null) : NeonButton(context, "Raw sanitizado", onClick = onClick) {
    init {
        contentDescription = "Abrir raw sanitizado por referencia $rawRef"
    }
}

