package br.com.aipinho.mobile.ui.cards

import android.content.Context
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.ArtifactDownloadRepository
import br.com.aipinho.mobile.network.ArtifactClient
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import org.json.JSONObject

data class ChatArtifactLinkView(
    val artifactId: String,
    val filename: String,
    val contentType: String,
    val label: String,
)

class ArtifactLinkRenderer {
    fun renderInto(
        context: Context,
        container: LinearLayout,
        payload: String,
        artifactClient: ArtifactClient,
        tokenProvider: () -> String?,
        fallbackArtifactId: String? = null,
        fallbackFilename: String? = null,
        fallbackContentType: String? = null,
    ) {
        container.removeAllViews()
        val links = extract(payload).ifEmpty {
            val artifactId = fallbackArtifactId?.takeIf { it.isNotBlank() } ?: return
            listOf(
                ChatArtifactLinkView(
                    artifactId = artifactId,
                    filename = fallbackFilename?.takeIf { it.isNotBlank() } ?: "artifact",
                    contentType = fallbackContentType?.takeIf { it.isNotBlank() } ?: "application/octet-stream",
                    label = "Baixar ${fallbackFilename?.takeIf { it.isNotBlank() } ?: "artifact"}",
                ),
            )
        }
        links.forEach { link ->
            container.addView(card(context, link, artifactClient, tokenProvider))
        }
    }

    fun extract(payload: String): List<ChatArtifactLinkView> {
        if (payload.isBlank()) return emptyList()
        return runCatching {
            val root = JSONObject(payload)
            val links = mutableListOf<ChatArtifactLinkView>()
            collectFromPresentation(root, links)
            collectFromChatResponse(root, links)
            links.distinctBy { it.artifactId }
        }.getOrDefault(emptyList())
    }

    private fun collectFromPresentation(root: JSONObject, links: MutableList<ChatArtifactLinkView>) {
        val messages = root.optJSONObject("presentation")?.optJSONArray("messages") ?: return
        for (messageIndex in 0 until messages.length()) {
            val message = messages.optJSONObject(messageIndex) ?: continue
            val artifacts = message.optJSONArray("artifacts") ?: continue
            for (artifactIndex in 0 until artifacts.length()) {
                val artifact = artifacts.optJSONObject(artifactIndex) ?: continue
                appendArtifact(artifact, links)
            }
        }
    }

    private fun collectFromChatResponse(root: JSONObject, links: MutableList<ChatArtifactLinkView>) {
        val chatResponse = root.optJSONObject("chat_response") ?: root
        val artifacts = chatResponse.optJSONArray("artifact_links") ?: return
        for (index in 0 until artifacts.length()) {
            val artifact = artifacts.optJSONObject(index) ?: continue
            appendArtifact(artifact, links)
        }
    }

    private fun appendArtifact(artifact: JSONObject, links: MutableList<ChatArtifactLinkView>) {
        if (artifact.optString("status", "ready") == "degraded") return
        val artifactId = artifact.optString("artifact_id").takeIf { it.isNotBlank() } ?: return
        val filename = artifact.optString("filename").takeIf { it.isNotBlank() } ?: "artifact"
        val contentType = artifact.optString("content_type").takeIf { it.isNotBlank() } ?: "application/octet-stream"
        val label = artifact.optString("label").takeIf { it.isNotBlank() } ?: "Baixar $filename"
        links.add(ChatArtifactLinkView(artifactId, filename, contentType, label))
    }

    private fun card(
        context: Context,
        link: ChatArtifactLinkView,
        artifactClient: ArtifactClient,
        tokenProvider: () -> String?,
    ): NeonCyberCard {
        return NeonCyberCard(context, "Artifact", "Download autenticado").apply {
            addBody(link.filename)
            addBody(link.contentType)
            ArtifactDownloadRepository(context)
                .findLatestByArtifactId(link.artifactId)
                ?.statusText
                ?.takeIf { it.isNotBlank() }
                ?.let { addBody(it) }
            addView(NeonButton(context, link.label) {
                if (tokenProvider().isNullOrBlank()) {
                    addBody("Token ausente. Configure o token local antes de baixar.", error = true)
                    return@NeonButton
                }
                addBody("Preparando download...")
                val downloadId = runCatching {
                    artifactClient.download(context, link.artifactId, link.filename, link.contentType)
                }.getOrElse { error ->
                    addBody("Falha no download: ${error.message ?: "erro desconhecido"}", error = true)
                    return@NeonButton
                }
                addBody("Download iniciado no gerenciador Android ($downloadId). A notificacao mostrara o resultado.")
            })
        }
    }
}
