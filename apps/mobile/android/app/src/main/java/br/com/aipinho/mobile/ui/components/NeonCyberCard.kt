package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonSpacing

open class NeonCyberCard(context: Context, title: String = "", subtitle: String = "") : LinearLayout(context) {
    init {
        orientation = VERTICAL
        background = AipinhoNeonTheme.rounded(context, fill = NeonColors.cardBlueGray, stroke = NeonColors.neonCyan)
        val pad = AipinhoNeonTheme.dp(context, NeonSpacing.medium)
        setPadding(pad, pad, pad, pad)
        if (title.isNotBlank()) addView(titleView(title))
        if (subtitle.isNotBlank()) addView(metadataView(subtitle))
    }

    fun titleView(value: String): TextView = TextView(context).apply {
        text = value
        AipinhoNeonTheme.styleTitle(this)
    }

    fun metadataView(value: String): TextView = TextView(context).apply {
        text = value
        AipinhoNeonTheme.styleMetadata(this)
    }

    fun bodyView(value: String, error: Boolean = false): TextView = TextView(context).apply {
        text = value
        AipinhoNeonTheme.styleLog(this, error = error)
    }

    fun addBody(value: String, error: Boolean = false): TextView {
        val view = bodyView(value, error)
        addView(view)
        return view
    }
}
