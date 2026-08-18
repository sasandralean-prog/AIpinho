package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class PipelinePermissionLogTest {
    @Test fun pipelineShowsPermissionAsLogNotExecutionBypass() {
        val source = NeonSourceContract.source("ui/screens/PipelineScreen.kt")
        assertTrue(source.contains("HumanizedViewModelTerminal"))
        assertTrue(source.contains("mobileViewModels.pipeline()"))
        assertTrue(source.contains("mobileViewModels.pipeline(\"active\")"))
        assertTrue(source.contains("\"Somente task ativa\""))
        assertTrue(source.contains("/api/v1/mobile/view-model/pipeline") || NeonSourceContract.source("network/MobileViewModelClient.kt").contains("/api/v1/mobile/view-model/pipeline"))
    }
}
