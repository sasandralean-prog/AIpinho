package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.view.MotionEvent
import android.view.View
import android.view.ViewParent
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonSpacing

class NeonLogTerminal(context: Context) : ScrollView(context) {
    private val body = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
    private val currentLines = mutableListOf<String>()

    init {
        background = AipinhoNeonTheme.rounded(context, fill = NeonColors.terminalBlack, stroke = NeonColors.neonCyan, radiusDp = 14)
        val pad = AipinhoNeonTheme.dp(context, NeonSpacing.small)
        setPadding(pad, pad, pad, pad)
        isFillViewport = false
        isVerticalScrollBarEnabled = true
        isScrollbarFadingEnabled = false
        isNestedScrollingEnabled = true
        isSmoothScrollingEnabled = true
        overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS
        minimumHeight = AipinhoNeonTheme.dp(context, 180)
        addView(body, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
    }

    fun setLines(lines: List<String>, error: Boolean = false) {
        body.removeAllViews()
        currentLines.clear()
        lines.forEach { appendLine(it, error = error) }
    }

    fun addLine(line: String, error: Boolean = false): TextView {
        val view = appendLine(line, error)
        return view
    }

    fun copyText(): String = currentLines.joinToString("\n")

    private fun appendLine(line: String, error: Boolean): TextView {
        currentLines.add(line)
        val view = TextView(context).apply {
            text = line
            setTextIsSelectable(true)
            AipinhoNeonTheme.styleLog(this, error = error)
        }
        body.addView(view)
        return view
    }

    private fun hasScrollableContent(): Boolean =
        body.height > height + AipinhoNeonTheme.dp(context, 4)

    private fun requestAncestorsDisallowIntercept(disallow: Boolean) {
        var current: ViewParent? = parent
        while (current != null) {
            current.requestDisallowInterceptTouchEvent(disallow)
            current = current.parent
        }
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        val ownsGesture = hasScrollableContent() || canScrollVertically(-1) || canScrollVertically(1)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN,
            MotionEvent.ACTION_MOVE,
            MotionEvent.ACTION_POINTER_DOWN -> requestAncestorsDisallowIntercept(ownsGesture)
            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_CANCEL,
            MotionEvent.ACTION_POINTER_UP -> requestAncestorsDisallowIntercept(false)
        }
        return super.dispatchTouchEvent(event)
    }
}
