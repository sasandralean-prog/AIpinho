package br.com.aipinho.mobile.ui.cards

import android.content.Context
import br.com.aipinho.mobile.ui.components.NeonCyberCard

class SanitizedCopyPanel(context: Context, copyPolicy: String = "sanitized_only") : NeonCyberCard(context, "Copy", copyPolicy) {
    init {
        addBody("Resumo sanitizado copiavel; raw somente por raw_ref e nunca visivel por padrao.")
    }
}

