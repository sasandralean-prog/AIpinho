package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography

open class NeonStatusBadge(context: Context, status: String) : TextView(context) {
    init {
        text = " $status "
        textSize = NeonTypography.metadataSp
        typeface = NeonTypography.terminalTypeface
        setTextColor(if (status.contains("down", true) || status.contains("erro", true)) NeonColors.dangerPink else NeonColors.neonCyan)
        background = AipinhoNeonTheme.rounded(context, fill = NeonColors.terminalDarkGray, stroke = currentTextColor, radiusDp = 12)
    }
}
