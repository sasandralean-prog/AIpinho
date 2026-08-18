package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class NeonThemeTest {
    @Test fun sprintPaletteIsCentralized() {
        val source = NeonSourceContract.source("ui/theme/NeonColors.kt")
        listOf("#020406", "#00E5FF", "#39FF14", "#FF2BD6").forEach {
            assertTrue(source.contains(it))
        }
    }
}
