package br.com.aipinho.mobile.ui.theme

import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.view.View
import android.widget.TextView

object AipinhoNeonTheme {
    fun dp(context: Context, value: Int): Int = (value * context.resources.displayMetrics.density).toInt()

    fun rounded(
        context: Context,
        fill: Int = NeonColors.cardBlueGray,
        stroke: Int = NeonColors.neonCyan,
        radiusDp: Int = NeonShapes.cardRadiusDp,
        strokeDp: Int = 1,
    ): GradientDrawable = GradientDrawable().apply {
        setColor(fill)
        cornerRadius = dp(context, radiusDp).toFloat()
        setStroke(dp(context, strokeDp), stroke)
    }

    fun applyScreen(view: View) {
        view.setBackgroundColor(NeonColors.matrixBlack)
    }

    fun styleTitle(text: TextView) {
        text.setTextColor(NeonColors.neonPink)
        text.textSize = NeonTypography.titleSp
        text.typeface = NeonTypography.terminalTypeface
    }

    fun styleMetadata(text: TextView) {
        text.setTextColor(NeonColors.neonCyan)
        text.textSize = NeonTypography.metadataSp
        text.typeface = NeonTypography.terminalTypeface
    }

    fun styleLog(text: TextView, error: Boolean = false) {
        text.setTextColor(if (error) NeonColors.dangerPink else NeonColors.neonGreen)
        text.textSize = NeonTypography.bodySp
        text.typeface = NeonTypography.terminalTypeface
    }
}
