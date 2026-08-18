package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonArtifactCard(context: Context, artifactId: String, detail: String) : NeonCyberCard(context, "Artifact", artifactId) {
    init {
        addBody(detail)
        addView(NeonCopyButton(context, "Copiar artifact_id") { artifactId })
    }
}
