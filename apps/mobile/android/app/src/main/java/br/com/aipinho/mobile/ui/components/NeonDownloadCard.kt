package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonDownloadCard(context: Context, status: String = "Download apenas por artifact_id.") : NeonCyberCard(context, "Download") {
    init { addBody(status) }
}
