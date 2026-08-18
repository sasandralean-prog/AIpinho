package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme

class NeonTerminalCard(context: Context, title: String, lines: List<String> = emptyList(), minHeightDp: Int = 180) : NeonCyberCard(context, title) {
    val terminal = NeonLogTerminal(context)

    init {
        terminal.minimumHeight = AipinhoNeonTheme.dp(context, minHeightDp)
        addView(terminal, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, AipinhoNeonTheme.dp(context, minHeightDp)))
        terminal.setLines(lines)
        addView(NeonCopyButton(context) { terminal.copyText() })
    }
}
