package br.com.aipinho.mobile.ui.components

import android.content.Context

class NeonFilterChip(context: Context, label: String, selected: Boolean = false, onClick: (() -> Unit)? = null) : NeonButton(context, label, selected, onClick)
