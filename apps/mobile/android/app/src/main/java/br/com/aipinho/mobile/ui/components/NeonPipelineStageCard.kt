package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonPipelineStageCard(context: Context, stage: String, status: String, detail: String) : NeonCyberCard(context, stage, status) {
    init { addBody(detail, error = status.contains("failed", true) || status.contains("blocked", true)) }
}
