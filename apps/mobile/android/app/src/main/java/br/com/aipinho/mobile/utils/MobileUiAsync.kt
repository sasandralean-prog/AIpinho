package br.com.aipinho.mobile.utils

import android.app.Activity
import android.content.Context
import android.widget.TextView

object MobileUiAsync {
    fun run(context: Context, onResult: (String) -> Unit, block: () -> String) {
        Thread {
            val text = runCatching(block).getOrElse { error -> "Erro: ${Redaction.redact(error.message.orEmpty())}" }
            (context as? Activity)?.runOnUiThread { onResult(Redaction.redact(text)) }
        }.start()
    }

    fun update(context: Context, target: TextView, block: () -> String) {
        run(context, { target.text = it }, block)
    }
}
