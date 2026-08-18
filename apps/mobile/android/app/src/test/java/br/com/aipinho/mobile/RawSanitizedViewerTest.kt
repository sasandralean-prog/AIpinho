package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class RawSanitizedViewerTest {
    @Test fun rawCopyButtonUsesSanitizedClipboardPath() {
        val source = NeonSourceContract.source("ui/components/NeonRawCopyButton.kt")
        assertTrue(source.contains("NeonCopyButton"))
        assertTrue(source.contains("Copiar raw sanitizado"))
    }
}
