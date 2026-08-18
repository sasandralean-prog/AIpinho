package br.com.aipinho.mobile.ui.cards

import android.content.Context
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.utils.Redaction

open class HumanizedStatusCard(context: Context, title: String, private val fallback: String) : NeonCyberCard(context, title, "Mobile View Model") {
    init {
        addBody(fallback)
    }

    fun updateFromJson(body: String) {
        removeAllViews()
        addView(titleView("Mobile View Model"))
        addView(metadataView("sanitized human cards"))
        val visible = Redaction.redact(body)
            .replace("{", "{\n")
            .replace("}", "\n}")
            .replace(",", ",\n")
            .lineSequence()
            .filter { line ->
                line.contains("human_summary") ||
                    line.contains("what_is_happening") ||
                    line.contains("why_is_it_happening") ||
                    line.contains("is_it_safe") ||
                    line.contains("what_can_i_do_now") ||
                    line.contains("can_copy_sanitized_summary") ||
                    line.contains("title") ||
                    line.contains("status") ||
                    line.contains("severity") ||
                    line.contains("disabled_reason")
            }
            .take(80)
            .joinToString("\n")
            .ifBlank { fallback }
        addBody(visible)
    }
}
