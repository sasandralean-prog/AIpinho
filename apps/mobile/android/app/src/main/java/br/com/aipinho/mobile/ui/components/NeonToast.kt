package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.Toast

object NeonToast {
    fun show(context: Context, message: String) = Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
}
