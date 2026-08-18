package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonRawCopyButton(context: Context, textProvider: () -> String) : NeonCopyButton(context, "Copiar raw", textProvider) {
    init {
        contentDescription = "Copiar raw sanitizado"
    }
}
