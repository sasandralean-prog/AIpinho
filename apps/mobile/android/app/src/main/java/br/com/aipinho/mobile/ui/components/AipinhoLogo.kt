package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme

class AipinhoLogo(context: Context) : TextView(context) {
    init {
        text = "AIpinho"
        AipinhoNeonTheme.styleTitle(this)
    }
}
