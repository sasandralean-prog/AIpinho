package br.com.aipinho.mobile.ui.components

import android.content.Context
import br.com.aipinho.mobile.utils.ClipboardUtils

open class NeonCopyButton(context: Context, label: String = "Copiar", textProvider: () -> String) : NeonButton(context, label, onClick = {
    ClipboardUtils.copy(context, label, textProvider())
})
