package br.com.aipinho.mobile.network

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.utils.SafeUrlBuilder

class ArtifactDownloadManager(
    private val profile: ConnectionProfile,
    private val tokenProvider: () -> String?,
) {
    companion object {
        const val PUBLIC_DOWNLOAD_SUBDIR = "AIpinhodownloads"
    }

    fun enqueue(
        context: Context,
        artifactId: String,
        filename: String,
        contentType: String,
        downloadEndpoint: String? = null,
    ): Long {
        require(artifactId.matches(Regex("artifact_[A-Za-z0-9_-]+"))) { "invalid_artifact_id" }
        val token = tokenProvider()?.takeIf { it.isNotBlank() }
            ?: throw IllegalStateException("local_token_required")
        val path = canonicalDownloadPath(downloadEndpoint, artifactId)
        val port = if (path.startsWith("/api/v1/artifacts/")) profile.artifactPort else profile.corePort
        val request = DownloadManager.Request(Uri.parse(SafeUrlBuilder.build(profile.host, port, path)))
            .setTitle(filename)
            .setDescription("Download governado pela AIpinho")
            .setMimeType(contentType)
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "$PUBLIC_DOWNLOAD_SUBDIR/$filename")
        request.addRequestHeader("Authorization", "Bearer $token")
        val manager = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val downloadId = manager.enqueue(request)
        ArtifactDownloadNotifier(context.applicationContext).monitor(downloadId, filename, artifactId, contentType)
        return downloadId
    }

    private fun canonicalDownloadPath(downloadEndpoint: String?, artifactId: String): String {
        val endpoint = downloadEndpoint?.trim().orEmpty()
        if (endpoint.startsWith("/") && !endpoint.contains("://") && !endpoint.contains("?")) {
            return endpoint
        }
        return "/api/v1/artifacts/$artifactId/download"
    }
}
