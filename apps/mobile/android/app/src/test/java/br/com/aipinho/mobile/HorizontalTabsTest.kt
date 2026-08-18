package br.com.aipinho.mobile

import br.com.aipinho.mobile.ui.navigation.MainTab
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HorizontalTabsTest {
    @Test
    fun mainTabsMatchCurrentProductContract() {
        assertEquals(
            listOf("Dashboard", "Chat", "Gemini", "Codex", "Pipeline", "Approvers", "Debugger 2.0", "Config"),
            MainTab.entries.map { it.label },
        )
        val source = NeonSourceContract.source("ui/components/AipinhoScrollableTabBar.kt")
        assertTrue(source.contains("HorizontalScrollView"))
    }
}
