package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class ArtifactDownloadCopyTest {
    @Test fun artifactCardsExposeCopyAndDownloadActions() {
        assertTrue(NeonSourceContract.source("ui/components/NeonArtifactCard.kt").contains("NeonCopyButton"))
        assertTrue(NeonSourceContract.source("ui/components/NeonDownloadCard.kt").contains("Download"))
        val renderer = NeonSourceContract.source("ui/cards/ArtifactLinkRenderer.kt")
        assertTrue(renderer.contains("presentation"))
        assertTrue(renderer.contains("artifact_links"))
        assertTrue(renderer.contains("Token ausente"))
        assertTrue(renderer.contains("Preparando download"))
        assertTrue(renderer.contains("Download iniciado"))
        assertTrue(renderer.contains("A notificacao mostrara o resultado"))
        assertTrue(renderer.contains("Falha no download"))
        assertTrue(renderer.contains("ArtifactDownloadRepository"))
        assertTrue(renderer.contains("findLatestByArtifactId"))
        assertTrue(renderer.contains("artifactClient.download"))
        assertTrue(renderer.contains("degraded"))
        assertTrue(!renderer.contains("ACTION_VIEW"))
        assertTrue(!renderer.contains("download_endpoint"))
        val client = NeonSourceContract.source("network/ArtifactClient.kt")
        assertTrue(client.contains("/api/v1/artifacts/upload"))
        assertTrue(client.contains("artifact_ids"))
        val manager = NeonSourceContract.source("network/ArtifactDownloadManager.kt")
        assertTrue(manager.contains("local_token_required"))
        assertTrue(manager.contains("Authorization"))
        assertTrue(manager.contains("Bearer \$token"))
        assertTrue(manager.contains("/api/v1/artifacts/\$artifactId/download"))
        assertTrue(manager.contains("AIpinhodownloads"))
        assertTrue(manager.contains("setDestinationInExternalPublicDir"))
        val manifest = java.io.File("src/main/AndroidManifest.xml").readText()
        assertTrue(manifest.contains("ArtifactDownloadCompleteReceiver"))
        assertTrue(manifest.contains("android:exported=\"true\""))
    }
}
