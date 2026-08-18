package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.view.Gravity
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import br.com.aipinho.mobile.ui.navigation.MainTab
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors

class AipinhoScrollableTabBar(
    context: Context,
    selected: MainTab,
    serviceState: Map<MainTab, String> = emptyMap(),
    onSelect: (MainTab) -> Unit,
) : HorizontalScrollView(context) {
    init {
        isHorizontalScrollBarEnabled = false
        setBackgroundColor(NeonColors.matrixBlack)
        val row = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(AipinhoNeonTheme.dp(context, 4), AipinhoNeonTheme.dp(context, 6), AipinhoNeonTheme.dp(context, 4), AipinhoNeonTheme.dp(context, 6))
        }
        MainTab.values().forEach { tab ->
            val badge = serviceState[tab]?.let { " [$it]" }.orEmpty()
            row.addView(NeonButton(context, "${tab.icon} ${tab.label}$badge", selected = tab == selected) { onSelect(tab) })
        }
        addView(row)
    }
}
