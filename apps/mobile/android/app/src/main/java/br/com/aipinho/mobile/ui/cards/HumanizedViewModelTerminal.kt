package br.com.aipinho.mobile.ui.cards

import android.content.Context
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import br.com.aipinho.mobile.ui.cards.ChatPresentationRenderer
import br.com.aipinho.mobile.ui.components.NeonFilterChip
import br.com.aipinho.mobile.ui.components.NeonTerminalCard
import br.com.aipinho.mobile.utils.Redaction
import org.json.JSONArray
import org.json.JSONObject

class HumanizedViewModelTerminal(
    context: Context,
    title: String,
    private val minHeightDp: Int = 340,
) : LinearLayout(context) {
    private val terminal = NeonTerminalCard(
        context,
        title,
        listOf("Aguardando /api/v1/mobile/view-model/*..."),
        minHeightDp = minHeightDp,
    )
    private var sourceLines: List<String> = emptyList()
    private var activeFilter = "todos"
    private val filters = listOf("todos", "status", "eventos", "evidencia", "acoes", "timeline", "raw_ref")
    private val chatPresentation = ChatPresentationRenderer()

    init {
        orientation = LinearLayout.VERTICAL
        addView(HorizontalScrollView(context).apply {
            isHorizontalScrollBarEnabled = false
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                filters.forEach { label ->
                    addView(NeonFilterChip(context, label, selected = label == activeFilter) {
                        activeFilter = label
                        render()
                    })
                }
            })
        })
        addView(terminal)
    }

    fun setPayload(body: String, fallback: String = "view_model_unavailable") {
        sourceLines = normalize(Redaction.redact(body.ifBlank { fallback }))
        render()
    }

    fun clear(message: String = "Cockpit limpo. A conversa persistida nao foi apagada.") {
        sourceLines = listOf(message)
        activeFilter = "todos"
        render()
    }

    fun copyText(): String = sourceLines.joinToString("\n")

    private fun render() {
        val filtered = when (activeFilter) {
            "status" -> sourceLines.filterAny("status", "severity", "healthy", "degraded", "blocked", "unknown", "failed", "pending", "running")
            "eventos" -> sourceLines.filterAny("event", "event_ids", "trace", "debugger", "filter")
            "evidencia" -> sourceLines.filterAny("evidence", "what_evidence_supports_this", "ref_id", "human_label", "citation", "memory")
            "acoes" -> sourceLines.filterAny("safe_actions", "what_can_i_do_now", "action_id", "enabled", "disabled_reason", "endpoint_ref")
            "timeline" -> sourceLines.filterAny("timeline", "phase", "task", "run", "validation", "approval", "patch", "artifact")
            "raw_ref" -> sourceLines.filterAny("raw_ref", "raw_available", "raw_default_visible", "copy_policy")
            else -> sourceLines
        }
        terminal.terminal.setLines(filtered.ifEmpty { listOf("Sem itens para filtro: $activeFilter") })
    }

    private fun normalize(text: String): List<String> {
        humanizedLines(text)?.let { return it }
        return text
            .replace("{", "{\n")
            .replace("}", "\n}")
            .replace("[", "[\n")
            .replace("]", "\n]")
            .replace(",", ",\n")
            .lineSequence()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .toList()
    }

    private fun humanizedLines(text: String): List<String>? {
        return runCatching {
            val root = JSONObject(text)
            root.optJSONObject("presentation")?.let {
                return@runCatching chatPresentation.normalLines(text)
            }
            val lines = mutableListOf<String>()
            root.optJSONObject("state")?.let { state ->
                lines.add("status: ${state.optString("status", "unknown")}")
                state.optString("human_summary").takeIf { it.isNotBlank() }?.let { lines.add("timeline resumo: $it") }
                lines.add("raw_default_visible: ${state.optBoolean("raw_default_visible", false)}")
            }
            val cards = root.optJSONArray("cards") ?: JSONArray()
            for (index in 0 until cards.length()) {
                val card = cards.optJSONObject(index) ?: continue
                val title = card.optString("title", "Card")
                val type = card.optString("card_type", "unknown")
                val status = card.optString("status", "unknown")
                val severity = card.optString("severity", "info")
                val answers = card.optJSONObject("answers")
                lines.add("")
                lines.add("timeline card: $title")
                lines.add("status: $status severity: $severity type: $type")
                answers?.optString("what_is_happening")?.takeIf { it.isNotBlank() }?.let { lines.add("acontecendo: $it") }
                answers?.optString("why_is_it_happening")?.takeIf { it.isNotBlank() }?.let { lines.add("por_que: $it") }
                answers?.optJSONObject("is_it_safe")?.let { safety ->
                    lines.add("seguranca: ${safety.optString("answer", "unknown")} - ${safety.optString("reason", "")}")
                }
                appendArray(lines, "acoes", answers?.optJSONArray("what_can_i_do_now"))
                appendEvidence(lines, answers?.optJSONArray("what_evidence_supports_this"))
                appendMetadata(lines, card.optJSONObject("metadata"))
                card.optJSONObject("copy")?.let { copy ->
                    lines.add("copy_policy: ${copy.optString("copy_policy", "sanitized_only")} raw_available: ${copy.optBoolean("raw_available", false)}")
                }
                card.optString("raw_ref").takeIf { it.isNotBlank() && it != "null" }?.let { lines.add("raw_ref: $it") }
            }
            lines.map { line -> Redaction.redact(line) }.ifEmpty { null }
        }.getOrNull()
    }

    private fun appendArray(lines: MutableList<String>, label: String, values: JSONArray?) {
        if (values == null || values.length() == 0) return
        val items = (0 until values.length()).mapNotNull { values.optString(it).takeIf { item -> item.isNotBlank() } }
        if (items.isNotEmpty()) lines.add("$label: ${items.joinToString("; ")}")
    }

    private fun appendEvidence(lines: MutableList<String>, values: JSONArray?) {
        if (values == null || values.length() == 0) return
        for (index in 0 until values.length()) {
            val item = values.optJSONObject(index) ?: continue
            lines.add("evidencia: ${item.optString("human_label", "ref")} ref_id=${item.optString("ref_id", "")}")
        }
    }

    private fun appendMetadata(lines: MutableList<String>, metadata: JSONObject?) {
        if (metadata == null || metadata.length() == 0) return
        val interesting = listOf(
            "session_id",
            "message_id",
            "role",
            "task_id",
            "approval_required",
            "rag_used",
            "raw_available",
            "fallback_used",
            "real_inference",
            "universal_task_session_endpoint",
            "universal_task_events_endpoint",
            "universal_task_artifacts_endpoint",
            "external_collaboration_endpoint",
        )
        interesting.forEach { key ->
            if (metadata.has(key)) lines.add("metadata $key: ${metadata.optString(key)}")
        }
        appendUniversalTaskSession(lines, metadataObject(metadata, "universal_task_session"))
        appendExternalCollaboration(lines, metadataObject(metadata, "external_collaboration"))
    }

    private fun appendUniversalTaskSession(lines: MutableList<String>, session: JSONObject?) {
        if (session == null || session.length() == 0) return
        val progress = session.optJSONObject("progress")
        val approval = session.optJSONObject("approval_state")
        val validation = session.optJSONObject("validation_state")
        val artifact = session.optJSONObject("artifact_state")
        val result = session.optJSONObject("result_state")
        val links = session.optJSONObject("links")
        lines.add("sessao_universal task_run_id: ${session.optString("task_run_id", "-")}")
        lines.add("sessao_universal status: ${session.optString("status", "UNKNOWN")} phase: ${session.optString("phase", "-")} progress: ${progress?.optInt("percent", 0) ?: 0}% basis: ${progress?.optString("basis", "-") ?: "-"}")
        lines.add("sessao_universal current_step: ${session.optString("current_step", "-")} eta: ${session.optString("eta", "-")} updated_at: ${session.optString("updated_at", "-")}")
        lines.add("approval_state: ${approval?.optString("status", "unknown") ?: "unknown"} id: ${approval?.optString("approval_id", "-") ?: "-"}")
        lines.add("validation_state: ${validation?.optString("status", "unknown") ?: "unknown"} safe_to_report_success: ${validation?.optBoolean("safe_to_report_success", false) ?: false}")
        lines.add("artifact_state: ${artifact?.optString("status", "unknown") ?: "unknown"} count: ${artifact?.optInt("count", 0) ?: 0}")
        lines.add("result_state: ${result?.optString("status", "unknown") ?: "unknown"} safe_to_report_success: ${result?.optBoolean("safe_to_report_success", false) ?: false}")
        links?.optString("self")?.takeIf { it.isNotBlank() }?.let { lines.add("endpoint task_session: $it") }
        links?.optString("events")?.takeIf { it.isNotBlank() }?.let { lines.add("endpoint task_events: $it") }
        links?.optString("artifacts")?.takeIf { it.isNotBlank() }?.let { lines.add("endpoint task_artifacts: $it") }
    }

    private fun appendExternalCollaboration(lines: MutableList<String>, collaboration: JSONObject?) {
        if (collaboration == null || collaboration.length() == 0) return
        lines.add("ccr status: ${collaboration.optString("status", "none")} active: ${collaboration.optInt("active_count", 0)} total: ${collaboration.optInt("count", 0)}")
        val sessions = collaboration.optJSONArray("sessions") ?: return
        for (index in 0 until sessions.length()) {
            val item = sessions.optJSONObject(index) ?: continue
            lines.add("ccr sessao: ${item.optString("session_id", "-")} provider: ${item.optString("provider", "-")} status: ${item.optString("status", "-")} iteracao: ${item.optInt("review_iteration", 0)} estrategia: ${item.optString("retry_strategy", "-")}")
            item.optString("poll_endpoint").takeIf { it.isNotBlank() }?.let { lines.add("endpoint ccr_poll: $it") }
        }
    }

    private fun metadataObject(metadata: JSONObject, key: String): JSONObject? {
        metadata.optJSONObject(key)?.let { return it }
        val text = metadata.optString(key).trim()
        if (!text.startsWith("{") || !text.endsWith("}")) return null
        return runCatching { JSONObject(text) }.getOrNull()
    }

    private fun List<String>.filterAny(vararg terms: String): List<String> {
        return filter { line -> terms.any { term -> line.contains(term, ignoreCase = true) } }
    }
}
