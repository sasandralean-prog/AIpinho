package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class NeonCyberCardTest {
    @Test fun cyberCardUsesNeonBorderAndDarkSurface() {
        val source = NeonSourceContract.source("ui/components/NeonCyberCard.kt")
        assertTrue(source.contains("NeonColors.neonCyan"))
        assertTrue(source.contains("NeonColors.cardBlueGray"))
    }
}
