package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.widget.LinearLayout
import android.widget.Button
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography

open class NeonButton(
    context: Context,
    label: String,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
) : Button(context) {
    private val mainHandler = Handler(Looper.getMainLooper())

    init {
        text = label
        textSize = 12f
        typeface = NeonTypography.terminalTypeface
        renderState(selected)
        minWidth = AipinhoNeonTheme.dp(context, 132)
        minHeight = AipinhoNeonTheme.dp(context, 52)
        includeFontPadding = true
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply {
            setMargins(
                AipinhoNeonTheme.dp(context, 4),
                AipinhoNeonTheme.dp(context, 4),
                AipinhoNeonTheme.dp(context, 4),
                AipinhoNeonTheme.dp(context, 4),
            )
        }
        setPadding(AipinhoNeonTheme.dp(context, 10), AipinhoNeonTheme.dp(context, 5), AipinhoNeonTheme.dp(context, 10), AipinhoNeonTheme.dp(context, 5))
        setOnClickListener {
            renderState(true)
            onClick?.invoke()
            if (!selected) mainHandler.postDelayed({ renderState(false) }, 650)
        }
    }

    fun renderState(active: Boolean) {
        setTextColor(if (active) NeonColors.neonPink else NeonColors.neonCyan)
        background = AipinhoNeonTheme.rounded(
            context,
            fill = if (active) NeonColors.cardBlueGray else NeonColors.terminalDarkGray,
            stroke = if (active) NeonColors.neonPink else NeonColors.neonCyan,
            radiusDp = 14,
        )
    }
}
