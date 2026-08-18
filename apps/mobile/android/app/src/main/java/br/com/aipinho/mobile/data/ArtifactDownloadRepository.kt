package br.com.aipinho.mobile.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class PersistedArtifactDownload(
    val downloadId: Long,
    val artifactId: String,
    val filename: String,
    val contentType: String,
    val updatedAtMs: Long,
    val statusText: String = "",
    val terminal: Boolean = false,
)

class ArtifactDownloadRepository(context: Context) {
    private val prefs = context.getSharedPreferences("aipinho_artifact_downloads", Context.MODE_PRIVATE)

    fun save(download: PersistedArtifactDownload) {
        val current = list().filterNot { it.downloadId == download.downloadId }.toMutableList()
        current.add(download)
        persist(current.takeLast(MAX_DOWNLOADS))
    }

    fun list(): List<PersistedArtifactDownload> {
        val raw = prefs.getString("downloads", "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val downloadId = item.optLong("download_id", -1L)
                    val artifactId = item.optString("artifact_id").takeIf { it.isNotBlank() } ?: continue
                    val filename = item.optString("filename").takeIf { it.isNotBlank() } ?: "artifact"
                    val contentType = item.optString("content_type").takeIf { it.isNotBlank() } ?: "application/octet-stream"
                    if (downloadId > 0L) {
                        add(
                            PersistedArtifactDownload(
                                downloadId = downloadId,
                                artifactId = artifactId,
                                filename = filename,
                                contentType = contentType,
                                updatedAtMs = item.optLong("updated_at_ms", 0L),
                                statusText = item.optString("status_text"),
                                terminal = item.optBoolean("terminal", false),
                            ),
                        )
                    }
                }
            }
        }.getOrDefault(emptyList())
    }

    fun find(downloadId: Long): PersistedArtifactDownload? = list().firstOrNull { it.downloadId == downloadId }

    fun findLatestByArtifactId(artifactId: String): PersistedArtifactDownload? =
        list().filter { it.artifactId == artifactId }.maxByOrNull { it.updatedAtMs }

    fun updateStatus(downloadId: Long, statusText: String, terminal: Boolean) {
        val updated = list().map { download ->
            if (download.downloadId == downloadId) {
                download.copy(
                    statusText = statusText,
                    terminal = terminal,
                    updatedAtMs = System.currentTimeMillis(),
                )
            } else {
                download
            }
        }
        persist(updated.takeLast(MAX_DOWNLOADS))
    }

    fun prune(downloadIds: Set<Long>) {
        val now = System.currentTimeMillis()
        persist(
            list().filter {
                it.downloadId in downloadIds || (it.terminal && now - it.updatedAtMs < TERMINAL_RETENTION_MS)
            },
        )
    }

    private fun persist(downloads: List<PersistedArtifactDownload>) {
        val array = JSONArray()
        downloads.forEach { download ->
            array.put(
                JSONObject()
                    .put("download_id", download.downloadId)
                    .put("artifact_id", download.artifactId)
                    .put("filename", download.filename)
                    .put("content_type", download.contentType)
                    .put("updated_at_ms", download.updatedAtMs)
                    .put("status_text", download.statusText)
                    .put("terminal", download.terminal),
            )
        }
        prefs.edit().putString("downloads", array.toString()).apply()
    }

    companion object {
        private const val MAX_DOWNLOADS = 50
        private const val TERMINAL_RETENTION_MS = 24L * 60L * 60L * 1000L
    }
}
