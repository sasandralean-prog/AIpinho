package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors

class MobileScreenScaffold(
    context: Context,
    content: View,
    scrollable: Boolean = true,
) : FrameLayout(context) {
    init {
        setBackgroundColor(NeonColors.matrixBlack)
        val horizontalPadding = AipinhoNeonTheme.dp(context, 4)
        val bottomPadding = AipinhoNeonTheme.dp(context, 12)
        if (scrollable) {
            addView(
                ScrollView(context).apply {
                    isFillViewport = true
                    isVerticalScrollBarEnabled = false
                    isFocusable = true
                    isFocusableInTouchMode = true
                    descendantFocusability = FOCUS_BEFORE_DESCENDANTS
                    setPadding(horizontalPadding, 0, horizontalPadding, bottomPadding)
                    addView(
                        content,
                        LinearLayout.LayoutParams(
                            LinearLayout.LayoutParams.MATCH_PARENT,
                            LinearLayout.LayoutParams.WRAP_CONTENT,
                        ),
                    )
                },
                LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT),
            )
        } else {
            addView(
                content,
                LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT),
            )
        }
    }
}
