package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme

class NeonSectionHeader(context: Context, value: String) : TextView(context) {
    init {
        text = value
        AipinhoNeonTheme.styleTitle(this)
    }
}
