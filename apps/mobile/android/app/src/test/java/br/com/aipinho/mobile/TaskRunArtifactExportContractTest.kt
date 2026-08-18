package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class TaskRunArtifactExportContractTest {
    @Test
    fun artifactClientUsesGovernedTaskRunExportAndDownloadRoutes() {
        val client = NeonSourceContract.source("network/ArtifactClient.kt")
        val downloader = NeonSourceContract.source("network/ArtifactDownloadManager.kt")

        assertTrue(client.contains("/api/v1/artifacts/from-task-run/\$runId/summary-zip"))
        assertTrue(client.contains("summaryFilename:String=\"artifact.txt\""))
        assertTrue(client.contains("zipFilename:String=\"artifacts.zip\""))
        assertTrue(client.contains("ArtifactDownloadManager(profile, tokenProvider).enqueue"))
        assertTrue(downloader.contains("DownloadManager.Request"))
        assertTrue(downloader.contains("Authorization"))
        assertTrue(downloader.contains("setDestinationInExternalPublicDir"))
        assertTrue(downloader.contains("AIpinhodownloads"))
        assertTrue(downloader.contains("invalid_artifact_id"))
    }
}
