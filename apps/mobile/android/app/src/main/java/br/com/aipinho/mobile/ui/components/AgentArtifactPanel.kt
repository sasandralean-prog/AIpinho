package br.com.aipinho.mobile.ui.components

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import br.com.aipinho.mobile.network.ArtifactClient
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography
import org.json.JSONArray
import org.json.JSONObject

data class AgentArtifactView(
    val artifactId: String,
    val filename: String,
    val contentType: String,
    val downloadEndpoint: String?,
    val status: String,
    val errorReason: String?,
    val sizeBytes: Long,
    val sourceAgent: String?,
    val ownerTaskId: String?,
    val bridgeTaskId: String?,
    val validationStatus: String?,
    val localPath: String?,
)

class AgentArtifactPanel(
    context: Context,
    private val artifactClient: ArtifactClient,
) : NeonCyberCard(context, "Artifacts", "Entradas anexadas e resultados gerados") {
    private val inputState = bodyView("Entradas: nenhuma.")
    private val generatedContainer = LinearLayout(context).apply { orientation = VERTICAL }
    private val generatedScroll = NeonScrollablePanel(context).apply {
        isVerticalScrollBarEnabled = false
        body.addView(generatedContainer)
    }

    init {
        addView(inputState)
        addView(
            generatedScroll,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                AipinhoNeonTheme.dp(context, 220),
            ),
        )
        renderGenerated(emptyList())
    }

    fun renderInputs(names: List<String>) {
        inputState.text = if (names.isEmpty()) {
            "Entradas: nenhuma."
        } else {
            "Entradas anexadas:\n${names.joinToString("\n") { "- $it" }}"
        }
    }

    fun renderPayload(payload: String) {
        renderGenerated(parseArtifacts(payload))
    }

    private fun renderGenerated(artifacts: List<AgentArtifactView>) {
        generatedContainer.removeAllViews()
        if (artifacts.isEmpty()) {
            generatedContainer.addView(label("Nenhum artifact gerado nesta sessao."))
            return
        }
        artifacts.forEach { artifact ->
            generatedContainer.addView(
                NeonCyberCard(context, artifact.filename, artifact.contentType).apply {
                    addBody("ID: ${artifact.artifactId}")
                    addBody("Tamanho: ${formatSize(artifact.sizeBytes)}")
                    artifact.sourceAgent?.takeIf { it.isNotBlank() }?.let { addBody("Origem: $it") }
                    artifact.ownerTaskId?.takeIf { it.isNotBlank() }?.let { addBody("Task: $it") }
                    artifact.bridgeTaskId?.takeIf { it.isNotBlank() }?.let { addBody("Bridge task: $it") }
                    artifact.validationStatus?.takeIf { it.isNotBlank() }?.let { addBody("Validacao: $it") }
                    addView(NeonButton(context, "Copiar ID") { copy("artifact_id", artifact.artifactId) })
                    when (artifact.status) {
                        "ready" -> {
                            addBody("Pronto para download")
                            addView(NeonActionGroup(context, listOf(
                                NeonButton(context, "Baixar") {
                                    runCatching {
                                        artifactClient.download(
                                            context = context,
                                            artifactId = artifact.artifactId,
                                            filename = artifact.filename,
                                            contentType = artifact.contentType,
                                            downloadEndpoint = artifact.downloadEndpoint,
                                        )
                                    }.onFailure {
                                        addBody("Falha no download: ${it.message ?: "erro desconhecido"}", error = true)
                                    }
                                },
                            )))
                        }
                        "requested", "generating", "validating" -> addBody("Gerando artifact...")
                        "missing", "stale" -> addBody("Arquivo indisponivel: ${artifact.errorReason ?: "artifact stale ou missing"}", error = true)
                        "failed" -> addBody("Falhou: ${artifact.errorReason ?: "artifact indisponivel"}", error = true)
                        "blocked" -> addBody("Bloqueado: ${artifact.errorReason ?: "policy bloqueou a geracao"}", error = true)
                        "expired", "deleted" -> addBody("Indisponivel: ${artifact.status}", error = true)
                        else -> addBody("Status: ${artifact.status}")
                    }
                    artifact.localPath?.takeIf { it.isNotBlank() }?.let { path ->
                        addView(NeonButton(context, "Copiar caminho") { copy("artifact_path", path) })
                    }
                },
            )
        }
    }

    private fun parseArtifacts(payload: String): List<AgentArtifactView> {
        return runCatching {
            val root = JSONObject(payload)
            val items = root.optJSONArray("artifacts") ?: JSONArray()
            buildList {
                for (index in 0 until items.length()) {
                    val item = items.optJSONObject(index) ?: continue
                    val artifactId = item.optString("artifact_id").takeIf { it.isNotBlank() } ?: continue
                    add(
                        AgentArtifactView(
                            artifactId = artifactId,
                            filename = item.optString("filename").takeIf { it.isNotBlank() } ?: "artifact",
                            contentType = item.optString("content_type").takeIf { it.isNotBlank() }
                                ?: "application/octet-stream",
                            downloadEndpoint = item.optString("download_endpoint").takeIf { it.isNotBlank() },
                            status = item.optString("status").takeIf { it.isNotBlank() } ?: "ready",
                            errorReason = item.optString("error_reason").takeIf { it.isNotBlank() },
                            sizeBytes = item.optLong("size_bytes", item.optLong("size", 0L)),
                            sourceAgent = item.optString("source_agent").takeIf { it.isNotBlank() }
                                ?: item.optString("agent_id").takeIf { it.isNotBlank() },
                            ownerTaskId = item.optString("owner_task_id").takeIf { it.isNotBlank() }
                                ?: item.optString("run_id").takeIf { it.isNotBlank() },
                            bridgeTaskId = item.optString("bridge_task_id").takeIf { it.isNotBlank() }
                                ?: item.optString("delegation_id").takeIf { it.isNotBlank() },
                            validationStatus = item.optString("validation_status").takeIf { it.isNotBlank() },
                            localPath = item.optString("local_path").takeIf { it.isNotBlank() },
                        ),
                    )
                }
            }
        }.getOrDefault(emptyList())
    }

    private fun label(value: String): TextView = TextView(context).apply {
        text = value
        setTextColor(NeonColors.neonGreen)
        textSize = 14f
        typeface = NeonTypography.terminalTypeface
        setTextIsSelectable(true)
        visibility = View.VISIBLE
    }

    private fun copy(label: String, value: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        clipboard?.setPrimaryClip(ClipData.newPlainText(label, value))
    }

    private fun formatSize(bytes: Long): String {
        if (bytes < 1024L) return "$bytes B"
        val kib = bytes / 1024.0
        if (kib < 1024.0) return String.format("%.1f KB", kib)
        return String.format("%.1f MB", kib / 1024.0)
    }
}
