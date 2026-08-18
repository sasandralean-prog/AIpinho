package br.com.aipinho.mobile.ui.cards

import br.com.aipinho.mobile.utils.Redaction
import org.json.JSONObject

class ChatPresentationRenderer {
    fun normalLines(payload: String): List<String> = render(payload, "normal")
    fun detailsLines(payload: String): List<String> = render(payload, "details")
    fun rawLines(payload: String): List<String> = Redaction.redact(payload).lines().ifEmpty { listOf("Raw indisponivel.") }

    fun render(payload: String, mode: String): List<String> {
        return runCatching {
            val root = JSONObject(payload)
            val presentation = root.optJSONObject("presentation") ?: return@runCatching fallback(payload)
            when (mode) {
                "details" -> details(presentation)
                "raw" -> rawLines(payload)
                else -> normal(presentation)
            }
        }.getOrElse { fallback(payload) }
    }

    private fun normal(presentation: JSONObject): List<String> {
        val lines = mutableListOf<String>()
        val messages = presentation.optJSONArray("messages")
        if (messages != null) {
            for (index in 0 until messages.length()) {
                val message = messages.optJSONObject(index) ?: continue
                val label = message.optString("label", message.optString("role", "Mensagem"))
                val text = message.optString("text", "").trim()
                if (text.isNotBlank()) {
                    lines.add("$label:")
                    lines.add(text)
                    val artifacts = message.optJSONArray("artifacts")
                    if (artifacts != null) {
                        for (artifactIndex in 0 until artifacts.length()) {
                            val artifact = artifacts.optJSONObject(artifactIndex) ?: continue
                            if (artifact.optString("status", "ready") != "ready") continue
                            val artifactId = artifact.optString("artifact_id")
                            val labelText = artifact.optString("label").takeIf { it.isNotBlank() }
                                ?: artifact.optString("filename").takeIf { it.isNotBlank() }
                            if (artifactId.isNotBlank() && !labelText.isNullOrBlank()) {
                                lines.add(labelText)
                            }
                        }
                    }
                    lines.add("")
                }
            }
        }
        if (lines.isEmpty()) {
            presentation.optString("empty_state").takeIf { it.isNotBlank() }?.let { lines.add(it) }
        }
        val state = presentation.optJSONArray("state_lines")
        if (state != null && state.length() > 0) {
            lines.add("Estado")
            for (index in 0 until state.length()) {
                state.optString(index).takeIf { it.isNotBlank() }?.let { lines.add(it) }
            }
        }
        return lines.filter { it.isNotBlank() }.ifEmpty { listOf("Conversa carregada. Nenhuma mensagem para mostrar ainda.") }
    }

    private fun details(presentation: JSONObject): List<String> {
        val lines = mutableListOf<String>()
        val details = presentation.optJSONArray("details")
        if (details != null) {
            for (index in 0 until details.length()) {
                val detail = details.optJSONObject(index) ?: continue
                val label = detail.optString("label", "").trim()
                val value = detail.optString("value", "").trim()
                if (label.isNotBlank() && value.isNotBlank()) lines.add("$label: $value")
            }
        }
        return lines.ifEmpty { listOf("Nenhum detalhe tecnico relevante para esta conversa.") }
    }

    private fun fallback(payload: String): List<String> {
        return Redaction.redact(payload)
            .lines()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .ifEmpty { listOf("Historico humanizado indisponivel.") }
    }
}
