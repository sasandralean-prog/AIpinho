package br.com.aipinho.mobile.network

import android.content.Context
import br.com.aipinho.mobile.models.ConnectionProfile

class ArtifactClient(
    private val profile: ConnectionProfile,
    private val tokenProvider: () -> String?,
) : BaseApiClient(profile, profile.artifactPort, tokenProvider) {
    fun metadata(artifactId:String)=get("/api/v1/artifacts/$artifactId/metadata")
    fun manifest(artifactId:String)=get("/api/v1/artifacts/$artifactId/manifest")
    fun upload(filename:String,content:String,contentType:String="text/plain")=post("/api/v1/artifacts/upload","{\"filename\":${json(filename)},\"content\":${json(content)},\"encoding\":\"text\",\"content_type\":${json(contentType)}}")
    fun downloadPath(artifactId:String)="/api/v1/artifacts/$artifactId/download"
    fun zip(artifactIds:List<String>,filename:String="artifacts.zip")=post("/api/v1/artifacts/zip","{\"artifact_ids\":[${artifactIds.joinToString(","){json(it)}}],\"filename\":${json(filename)}}")
    fun exportTaskRunSummary(runId:String,summaryFilename:String="artifact.txt",zipFilename:String="artifacts.zip")=
        post(
            "/api/v1/artifacts/from-task-run/$runId/summary-zip",
            "{\"summary_filename\":${json(summaryFilename)},\"zip_filename\":${json(zipFilename)}}",
        )
    fun zipDownloadPath(artifactId:String)="/api/v1/artifacts/zip/$artifactId/download"
    fun download(
        context: Context,
        artifactId: String,
        filename: String,
        contentType: String,
        downloadEndpoint: String? = null,
    ): Long = ArtifactDownloadManager(profile, tokenProvider).enqueue(
        context,
        artifactId,
        filename,
        contentType,
        downloadEndpoint,
    )
    private fun json(value:String)=JsonPayload.string(value)
}
