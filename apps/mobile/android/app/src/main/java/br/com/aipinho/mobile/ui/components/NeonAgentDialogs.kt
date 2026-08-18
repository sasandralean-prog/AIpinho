package br.com.aipinho.mobile.ui.components

import android.app.AlertDialog
import android.content.Context
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography

object NeonAgentDialogs {
    fun sessionList(
        context: Context,
        title: String,
        sessions: List<Pair<String, String>>,
        onOpen: (String) -> Unit,
        onCreate: () -> Unit,
        onRename: (String, String) -> Unit,
        onDelete: (String) -> Unit,
    ) {
        val shell = shell(context, title)
        val list = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
        sessions.forEach { (sessionId, sessionTitle) ->
            list.addView(NeonCyberCard(context, sessionTitle, sessionId).apply {
                addView(LinearLayout(context).apply {
                    orientation = LinearLayout.HORIZONTAL
                    addView(NeonButton(context, "Abrir") { onOpen(sessionId) })
                    addView(NeonButton(context, "Renomear") {
                        rename(context, sessionTitle) { onRename(sessionId, it) }
                    })
                    addView(NeonButton(context, "Deletar") {
                        confirm(context, "Deletar sessao", "Remover '$sessionTitle' e seu historico?") {
                            onDelete(sessionId)
                        }
                    })
                })
            })
        }
        shell.addView(ScrollView(context).apply { addView(list) }, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            AipinhoNeonTheme.dp(context, 420),
        ))
        shell.addView(NeonButton(context, "Nova sessao") { onCreate() })
        show(context, shell)
    }

    fun rename(context: Context, currentTitle: String, onSave: (String) -> Unit) {
        val shell = shell(context, "Renomear chat")
        val input = EditText(context).apply {
            setText(currentTitle)
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            setSingleLine(true)
            setTextIsSelectable(true)
            background = AipinhoNeonTheme.rounded(
                context,
                fill = NeonColors.matrixBlack,
                stroke = NeonColors.neonCyan,
                radiusDp = 12,
            )
            setPadding(16, 12, 16, 12)
        }
        shell.addView(input)
        var dialog: AlertDialog? = null
        shell.addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(NeonButton(context, "Cancelar") { dialog?.dismiss() })
            addView(NeonButton(context, "Salvar") {
                val title = input.text.toString().trim()
                if (title.isNotBlank()) onSave(title)
                dialog?.dismiss()
            })
        })
        dialog = show(context, shell)
    }

    fun confirm(context: Context, title: String, message: String, onConfirm: () -> Unit) {
        val shell = shell(context, title)
        shell.addView(TextView(context).apply {
            text = message
            setTextColor(NeonColors.neonGreen)
            textSize = 15f
            typeface = NeonTypography.terminalTypeface
            setTextIsSelectable(true)
        })
        var dialog: AlertDialog? = null
        shell.addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(NeonButton(context, "Cancelar") { dialog?.dismiss() })
            addView(NeonButton(context, "Confirmar") {
                dialog?.dismiss()
                onConfirm()
            })
        })
        dialog = show(context, shell, NeonColors.neonPink)
    }

    private fun shell(context: Context, title: String) = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
        background = AipinhoNeonTheme.rounded(
            context,
            fill = NeonColors.matrixBlack,
            stroke = NeonColors.neonCyan,
            radiusDp = 20,
        )
        setPadding(16, 14, 16, 14)
        addView(TextView(context).apply {
            text = title
            setTextColor(NeonColors.neonCyan)
            textSize = 20f
            typeface = NeonTypography.terminalTypeface
            setTextIsSelectable(true)
        })
    }

    private fun show(
        context: Context,
        content: LinearLayout,
        stroke: Int = NeonColors.neonCyan,
    ): AlertDialog = AlertDialog.Builder(context)
        .setView(content)
        .create()
        .also { dialog ->
            dialog.setOnShowListener {
                dialog.window?.setBackgroundDrawable(
                    AipinhoNeonTheme.rounded(
                        context,
                        fill = NeonColors.matrixBlack,
                        stroke = stroke,
                        radiusDp = 20,
                    )
                )
            }
            dialog.show()
        }
}
