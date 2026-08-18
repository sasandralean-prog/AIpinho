package br.com.aipinho.mobile.ui.cards

import android.content.Context
import br.com.aipinho.mobile.ui.components.NeonCyberCard

class EvidenceCard(context: Context, title: String, ref: String) : NeonCyberCard(context, title, "Evidence") {
    init {
        addBody("Referencia sanitizada: $ref")
    }
}

