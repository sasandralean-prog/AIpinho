package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Scroller
import android.widget.EditText
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors

class NeonSearchField(context: Context, hintText: String) : EditText(context) {
    private val measuredMaxHeightPx = AipinhoNeonTheme.dp(context, 132)

    init {
        hint = hintText
        setTextColor(NeonColors.neonGreen)
        setHintTextColor(NeonColors.mutedCyan)
        background = AipinhoNeonTheme.rounded(context, fill = NeonColors.terminalBlack, stroke = NeonColors.neonCyan, radiusDp = 14)
        minLines = 2
        maxLines = 4
        maxHeight = AipinhoNeonTheme.dp(context, 132)
        gravity = Gravity.TOP or Gravity.START
        setSingleLine(false)
        setHorizontallyScrolling(false)
        setScroller(Scroller(context))
        isVerticalScrollBarEnabled = true
        overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        setPadding(AipinhoNeonTheme.dp(context, 8), AipinhoNeonTheme.dp(context, 6), AipinhoNeonTheme.dp(context, 8), AipinhoNeonTheme.dp(context, 6))
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val cappedHeightSpec = MeasureSpec.makeMeasureSpec(measuredMaxHeightPx, MeasureSpec.AT_MOST)
        super.onMeasure(widthMeasureSpec, cappedHeightSpec)
    }
}
