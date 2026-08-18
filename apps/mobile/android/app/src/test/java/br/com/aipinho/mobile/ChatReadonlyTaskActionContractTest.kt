package br.com.aipinho.mobile

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatReadonlyTaskActionContractTest {
    private val root = File(System.getProperty("user.dir") ?: ".")

    @Test
    fun chatUsesIntentDrivenArtifactFlowInsteadOfManualReadonlyButtons() {
        val source = File(
            root,
            "src/main/java/br/com/aipinho/mobile/ui/screens/ChatScreen.kt",
        ).readText()

        assertTrue(source.contains("syncLatestArtifactFromChatResponse"))
        assertTrue(source.contains("extractArtifactLink"))
        assertTrue(source.contains("saveLatestArtifact"))
        assertTrue(source.contains("latestArtifactId"))
        assertTrue(source.contains("ArtifactLinkRenderer"))
        assertTrue(source.contains("renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer)"))
        assertTrue(source.contains("tokenProvider = tokenProvider"))
        assertTrue(!source.contains("\"Iniciar analise\""))
        assertTrue(!source.contains("\"Atualizar analise\""))
        assertTrue(!source.contains("\"Exportar resumo\""))
        assertTrue(!source.contains("\"Baixar resumo.zip\""))
        assertTrue(!source.contains("NeonArtifactCard(context, \"artifact_id\""))
        assertTrue(!source.contains("ArtifactClient(SettingsRepository(context).loadProfile())"))
    }

    @Test
    fun runtimeClientUsesOfficialPreviewAndResultRoutes() {
        val source = File(
            root,
            "src/main/java/br/com/aipinho/mobile/network/TaskRuntimeClient.kt",
        ).readText()

        assertTrue(source.contains("/api/v1/task-runs/from-preview/"))
        assertTrue(source.contains("/api/v1/task-runs/"))
        assertTrue(source.contains("/start"))
        assertTrue(source.contains("/result"))
        assertTrue(source.contains("invalid_runtime_identifier"))
    }
}
