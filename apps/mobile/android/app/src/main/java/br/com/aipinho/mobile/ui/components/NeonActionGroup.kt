package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme

class NeonActionGroup(
    context: Context,
    actions: List<NeonButton>,
) : LinearLayout(context) {
    init {
        orientation = VERTICAL
        actions.chunked(2).forEach { chunk ->
            addView(LinearLayout(context).apply {
                orientation = HORIZONTAL
                chunk.forEach { button ->
                    button.minWidth = 0
                    button.layoutParams = LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply {
                        val margin = AipinhoNeonTheme.dp(context, 4)
                        setMargins(margin, margin, margin, margin)
                    }
                    addView(button)
                }
            })
        }
    }
}
