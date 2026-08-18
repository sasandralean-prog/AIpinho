package br.com.aipinho.mobile.ui.components

import android.content.Context
import android.widget.LinearLayout
import android.widget.ScrollView

class NeonScrollablePanel(context: Context) : ScrollView(context) {
    val body: LinearLayout = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }

    init {
        isFillViewport = false
        addView(body)
    }
}
