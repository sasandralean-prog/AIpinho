package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonPermissionRequestCard(
    context: Context,
    taskId: String,
    requestedAction: String,
    capability: String,
    risk: String,
    reason: String,
) : NeonCyberCard(context, "Permissão requerida", "task=$taskId") {
    private val payload = "task_id=$taskId\nrequested_action=$requestedAction\nrequired_capability=$capability\nrisk_level=$risk\nreason=$reason"
    init {
        addBody(payload, error = risk.contains("high", true))
        addView(NeonCopyButton(context, "Copiar permissão") { payload })
    }
}
