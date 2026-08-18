package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.TextView
import android.widget.Toast
import br.com.aipinho.mobile.utils.ClipboardUtils
import kotlin.math.max
import kotlin.math.min

object MessageCopySupport {
    fun makeSelectable(textView: TextView) {
        textView.setTextIsSelectable(true)
    }

    fun copySelectionOrLatest(
        context: Context,
        textView: TextView,
        latestMessage: String?,
        clipboardLabel: String,
    ) {
        val selectionStart = textView.selectionStart
        val selectionEnd = textView.selectionEnd
        val selectedText = if (selectionStart >= 0 && selectionEnd >= 0 && selectionStart != selectionEnd) {
            val start = min(selectionStart, selectionEnd)
            val end = max(selectionStart, selectionEnd)
            textView.text.subSequence(start, end).toString()
        } else {
            ""
        }
        val content = selectedText.ifBlank { latestMessage.orEmpty() }
        if (content.isBlank()) {
            Toast.makeText(context, "Nenhuma mensagem disponivel para copiar.", Toast.LENGTH_SHORT).show()
            return
        }
        ClipboardUtils.copy(context, clipboardLabel, content)
        val feedback = if (selectedText.isNotBlank()) "Texto selecionado copiado." else "Mensagem copiada."
        Toast.makeText(context, feedback, Toast.LENGTH_SHORT).show()
    }
}
