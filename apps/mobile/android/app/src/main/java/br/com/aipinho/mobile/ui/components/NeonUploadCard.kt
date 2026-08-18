package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonUploadCard(context: Context, status: String = "Upload governado por artifact service.") : NeonCyberCard(context, "Upload") {
    init { addBody(status) }
}
