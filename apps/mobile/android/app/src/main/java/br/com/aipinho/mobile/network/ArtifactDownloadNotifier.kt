package br.com.aipinho.mobile.network

import android.Manifest
import android.app.DownloadManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.database.Cursor
import android.os.Build
import br.com.aipinho.mobile.data.ArtifactDownloadRepository
import br.com.aipinho.mobile.data.PersistedArtifactDownload
import kotlin.concurrent.thread

class ArtifactDownloadNotifier(private val context: Context) {
    companion object {
        private const val CHANNEL_ID = "aipinho_artifact_downloads"
        private const val CHANNEL_NAME = "Downloads de artifacts"
    }

    private val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    fun notifyStarted(downloadId: Long, filename: String) {
        notify(downloadId, filename, "Iniciando download...", indeterminate = true, ongoing = true)
    }

    fun monitor(downloadId: Long, filename: String) {
        monitor(downloadId, filename, artifactId = "", contentType = "application/octet-stream")
    }

    fun monitor(downloadId: Long, filename: String, artifactId: String, contentType: String) {
        if (artifactId.isNotBlank()) {
            ArtifactDownloadRepository(context).save(
                PersistedArtifactDownload(
                    downloadId = downloadId,
                    artifactId = artifactId,
                    filename = filename,
                    contentType = contentType,
                    updatedAtMs = System.currentTimeMillis(),
                ),
            )
        }
        notifyStarted(downloadId, filename)
        thread(name = "aipinho-artifact-download-$downloadId", isDaemon = true) {
            val downloadManager = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            var finished = false
            while (!finished) {
                val snapshot = query(downloadManager, downloadId)
                when (snapshot.status) {
                    DownloadManager.STATUS_SUCCESSFUL -> {
                        updateStatus(downloadId, "Download concluido.", terminal = true)
                        notify(downloadId, filename, "Download concluido.", progress = 100, total = 100, ongoing = false, done = true)
                        pruneFinished(downloadId)
                        finished = true
                    }
                    DownloadManager.STATUS_FAILED -> {
                        val status = "Falha no download (${snapshot.reason})."
                        updateStatus(downloadId, status, terminal = true)
                        notify(downloadId, filename, status, ongoing = false, error = true)
                        pruneFinished(downloadId)
                        finished = true
                    }
                    DownloadManager.STATUS_RUNNING, DownloadManager.STATUS_PAUSED, DownloadManager.STATUS_PENDING -> {
                        val total = snapshot.totalBytes
                        val current = snapshot.downloadedBytes
                        val text = if (snapshot.status == DownloadManager.STATUS_PAUSED) "Download pausado..." else "Baixando artifact..."
                        updateStatus(downloadId, text, terminal = false)
                        if (total > 0 && current >= 0) {
                            notify(downloadId, filename, text, progress = current, total = total, ongoing = true)
                        } else {
                            notify(downloadId, filename, text, indeterminate = true, ongoing = true)
                        }
                    }
                    else -> notify(downloadId, filename, "Aguardando DownloadManager...", indeterminate = true, ongoing = true)
                }
                if (!finished) Thread.sleep(1000)
            }
        }
    }

    fun resumePersistedDownloads() {
        val repository = ArtifactDownloadRepository(context)
        val downloadManager = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val activeIds = mutableSetOf<Long>()
        repository.list().forEach { download ->
            val snapshot = query(downloadManager, download.downloadId)
            when (snapshot.status) {
                DownloadManager.STATUS_SUCCESSFUL -> {
                    updateStatus(download.downloadId, "Download concluido.", terminal = true)
                    notify(download.downloadId, download.filename, "Download concluido.", progress = 100, total = 100, ongoing = false, done = true)
                }
                DownloadManager.STATUS_FAILED -> {
                    val status = "Falha no download (${snapshot.reason})."
                    updateStatus(download.downloadId, status, terminal = true)
                    notify(download.downloadId, download.filename, status, ongoing = false, error = true)
                }
                DownloadManager.STATUS_RUNNING, DownloadManager.STATUS_PAUSED, DownloadManager.STATUS_PENDING -> {
                    activeIds.add(download.downloadId)
                    monitor(download.downloadId, download.filename, download.artifactId, download.contentType)
                }
            }
        }
        repository.prune(activeIds)
    }

    fun refreshPersistedDownload(downloadId: Long) {
        val repository = ArtifactDownloadRepository(context)
        val download = repository.find(downloadId) ?: return
        val downloadManager = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val snapshot = query(downloadManager, downloadId)
        when (snapshot.status) {
            DownloadManager.STATUS_SUCCESSFUL -> {
                updateStatus(download.downloadId, "Download concluido.", terminal = true)
                notify(download.downloadId, download.filename, "Download concluido.", progress = 100, total = 100, ongoing = false, done = true)
                pruneFinished(download.downloadId)
            }
            DownloadManager.STATUS_FAILED -> {
                val status = "Falha no download (${snapshot.reason})."
                updateStatus(download.downloadId, status, terminal = true)
                notify(download.downloadId, download.filename, status, ongoing = false, error = true)
                pruneFinished(download.downloadId)
            }
            DownloadManager.STATUS_RUNNING, DownloadManager.STATUS_PAUSED, DownloadManager.STATUS_PENDING -> {
                monitor(download.downloadId, download.filename, download.artifactId, download.contentType)
            }
        }
    }

    private fun query(downloadManager: DownloadManager, downloadId: Long): DownloadSnapshot {
        val cursor = downloadManager.query(DownloadManager.Query().setFilterById(downloadId))
        cursor.use {
            if (!it.moveToFirst()) return DownloadSnapshot(DownloadManager.STATUS_FAILED, -1, -1, "not_found")
            return DownloadSnapshot(
                status = it.int(DownloadManager.COLUMN_STATUS),
                downloadedBytes = it.long(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR),
                totalBytes = it.long(DownloadManager.COLUMN_TOTAL_SIZE_BYTES),
                reason = it.int(DownloadManager.COLUMN_REASON).toString(),
            )
        }
    }

    private fun notify(
        downloadId: Long,
        filename: String,
        text: String,
        progress: Long = 0,
        total: Long = 0,
        indeterminate: Boolean = false,
        ongoing: Boolean = false,
        done: Boolean = false,
        error: Boolean = false,
    ) {
        if (!notificationsAllowed()) return
        ensureChannel()
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(context, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(context)
        }
        val icon = when {
            error -> android.R.drawable.stat_notify_error
            done -> android.R.drawable.stat_sys_download_done
            else -> android.R.drawable.stat_sys_download
        }
        builder
            .setSmallIcon(icon)
            .setContentTitle(filename)
            .setContentText(text)
            .setOngoing(ongoing)
            .setOnlyAlertOnce(true)
            .setPriority(Notification.PRIORITY_LOW)
            .setShowWhen(true)
        if (indeterminate) {
            builder.setProgress(0, 0, true)
        } else if (total > 0) {
            val safeTotal = total.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
            val safeProgress = progress.coerceIn(0, total).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
            builder.setProgress(safeTotal, safeProgress, false)
        } else {
            builder.setProgress(0, 0, false)
        }
        manager.notify(downloadId.toInt(), builder.build())
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_LOW).apply {
            description = "Status de download de artifacts da AIpinho"
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)
    }

    private fun notificationsAllowed(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun Cursor.int(column: String): Int = getInt(getColumnIndexOrThrow(column))
    private fun Cursor.long(column: String): Long = getLong(getColumnIndexOrThrow(column))

    private fun pruneFinished(downloadId: Long) {
        val repository = ArtifactDownloadRepository(context)
        repository.prune(repository.list().map { it.downloadId }.filterNot { it == downloadId }.toSet())
    }

    private fun updateStatus(downloadId: Long, text: String, terminal: Boolean) {
        ArtifactDownloadRepository(context).updateStatus(downloadId, text, terminal)
    }
}

data class DownloadSnapshot(
    val status: Int,
    val downloadedBytes: Long,
    val totalBytes: Long,
    val reason: String,
)
